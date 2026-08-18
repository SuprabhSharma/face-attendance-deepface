import sqlite3
from datetime import datetime, timezone, timedelta
import json
import os
from hashlib import pbkdf2_hmac

# ✅ IST TIMEZONE
IST = timezone(timedelta(hours=5, minutes=30))

# ── DATABASE CONFIGURATION (Auto-detects PostgreSQL vs SQLite) ──
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

IS_POSTGRES = bool(DATABASE_URL)

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'attendance_system.db')
DB_PATH = os.path.abspath(os.getenv('DB_PATH', _DEFAULT_DB_PATH))

# Optional psycopg2 import for PostgreSQL
if IS_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        IS_POSTGRES = False
        print("Warning: psycopg2 not installed. Falling back to local SQLite.")


class DBConnectionWrapper:
    """Unified wrapper around SQLite and PostgreSQL connection."""
    def __init__(self, conn, is_postgres):
        self._conn = conn
        self.is_postgres = is_postgres

    def cursor(self):
        if self.is_postgres:
            return DBCursorWrapper(self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), True)
        return DBCursorWrapper(self._conn.cursor(), False)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def execute(self, sql, params=()):
        c = self.cursor()
        c.execute(sql, params)
        return c


class DBCursorWrapper:
    """Unified cursor that translates '?' placeholders to '%s' for PostgreSQL."""
    def __init__(self, cursor, is_postgres):
        self._cursor = cursor
        self.is_postgres = is_postgres

    def execute(self, sql, params=()):
        if self.is_postgres:
            # Convert '?' to '%s'
            sql_pg = sql.replace('?', '%s')
            return self._cursor.execute(sql_pg, params)
        return self._cursor.execute(sql, params)

    def executemany(self, sql, params_list):
        if self.is_postgres:
            sql_pg = sql.replace('?', '%s')
            return self._cursor.executemany(sql_pg, params_list)
        return self._cursor.executemany(sql, params_list)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if not self.is_postgres:
            return dict(row)
        return dict(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if not self.is_postgres:
            return [dict(r) for r in rows]
        return [dict(r) for r in rows]

    @property
    def lastrowid(self):
        if self.is_postgres:
            # For Postgres, lastrowid might be None if RETURNING was not used
            return getattr(self._cursor, 'lastrowid', None)
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        self._cursor.close()


def get_db_connection():
    """Get database connection (PostgreSQL if DATABASE_URL exists, otherwise SQLite)."""
    if IS_POSTGRES and DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        return DBConnectionWrapper(conn, is_postgres=True)
    
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return DBConnectionWrapper(conn, is_postgres=False)


def hash_password(password):
    """Hash password using PBKDF2"""
    salt = b'attendance_system_salt_2024'
    return pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()


def verify_password(password_hash, password):
    """Verify password against hash"""
    return password_hash == hash_password(password)


_db_is_initialized = False

def init_db(force=False):
    """Initialize database tables with fast one-time execution guard."""
    global _db_is_initialized
    if _db_is_initialized and not force:
        return

    conn = get_db_connection()
    c = conn.cursor()

    if conn.is_postgres:
        # ── PostgreSQL DDL ──
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                embedding TEXT,
                profile_picture TEXT,
                role VARCHAR(20) DEFAULT 'user' CHECK(role IN ('admin', 'user', 'manager')),
                status VARCHAR(20) DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
                is_verified INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')

        try:
            c.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture TEXT')
        except Exception:
            pass

        c.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                time_in TIME,
                time_out TIME,
                status VARCHAR(20) DEFAULT 'present' CHECK(status IN ('present', 'late', 'absent', 'half_day')),
                notes TEXT,
                marked_by VARCHAR(50) DEFAULT 'face_recognition',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, date)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON attendance(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date_user ON attendance(date, user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_user_date ON attendance(user_id, date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_status ON attendance(status)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS working_hours (
                id SERIAL PRIMARY KEY,
                day_of_week INTEGER UNIQUE,
                start_time TIME,
                end_time TIME,
                is_working_day INTEGER DEFAULT 1
            )
        ''')
        
        # Batch insert working hours
        c.execute('''
            INSERT INTO working_hours (day_of_week, start_time, end_time, is_working_day)
            VALUES 
                (0, '09:00:00', '17:00:00', 1),
                (1, '09:00:00', '17:00:00', 1),
                (2, '09:00:00', '17:00:00', 1),
                (3, '09:00:00', '17:00:00', 1),
                (4, '09:00:00', '17:00:00', 1),
                (5, '09:00:00', '17:00:00', 1),
                (6, '00:00:00', '00:00:00', 0)
            ON CONFLICT (day_of_week) DO NOTHING
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS attendance_reports (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                report_type TEXT CHECK(report_type IN ('daily', 'weekly', 'monthly')),
                report_date TEXT NOT NULL,
                total_present INTEGER DEFAULT 0,
                total_absent INTEGER DEFAULT 0,
                total_late INTEGER DEFAULT 0,
                total_half_day INTEGER DEFAULT 0,
                report_data TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, report_date)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_reports_date ON attendance_reports(report_date)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS email_notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                email_type TEXT CHECK(email_type IN ('attendance_marked', 'absent_notification', 'daily_summary', 'weekly_summary')),
                recipient_email TEXT NOT NULL,
                subject TEXT,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'sent', 'failed')),
                error_message TEXT,
                sent_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_emails_status ON email_notifications(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_emails_type ON email_notifications(email_type)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id INTEGER,
                details TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)')

    else:
        # ── SQLite DDL ──
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                embedding TEXT,
                profile_picture TEXT,
                role TEXT DEFAULT 'user' CHECK(role IN ('admin', 'user', 'manager')),
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
                is_verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')

        try:
            c.execute('ALTER TABLE users ADD COLUMN profile_picture TEXT')
        except Exception:
            pass

        c.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time_in TEXT,
                time_out TEXT,
                status TEXT DEFAULT 'present' CHECK(status IN ('present', 'late', 'absent', 'half_day')),
                notes TEXT,
                marked_by TEXT DEFAULT 'face_recognition',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, date)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON attendance(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date_user ON attendance(date, user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_user_date ON attendance(user_id, date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_status ON attendance(status)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS working_hours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_of_week INTEGER UNIQUE,
                start_time TEXT,
                end_time TEXT,
                is_working_day INTEGER DEFAULT 1
            )
        ''')
        
        # Batch insert for SQLite
        c.execute('''
            INSERT OR IGNORE INTO working_hours (day_of_week, start_time, end_time, is_working_day)
            VALUES 
                (0, '09:00:00', '17:00:00', 1),
                (1, '09:00:00', '17:00:00', 1),
                (2, '09:00:00', '17:00:00', 1),
                (3, '09:00:00', '17:00:00', 1),
                (4, '09:00:00', '17:00:00', 1),
                (5, '09:00:00', '17:00:00', 1),
                (6, '00:00:00', '00:00:00', 0)
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS attendance_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_type TEXT CHECK(report_type IN ('daily', 'weekly', 'monthly')),
                report_date TEXT NOT NULL,
                total_present INTEGER DEFAULT 0,
                total_absent INTEGER DEFAULT 0,
                total_late INTEGER DEFAULT 0,
                total_half_day INTEGER DEFAULT 0,
                report_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, report_date)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_reports_date ON attendance_reports(report_date)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS email_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_type TEXT CHECK(email_type IN ('attendance_marked', 'absent_notification', 'daily_summary', 'weekly_summary')),
                recipient_email TEXT NOT NULL,
                subject TEXT,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'sent', 'failed')),
                error_message TEXT,
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_emails_status ON email_notifications(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_emails_type ON email_notifications(email_type)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id INTEGER,
                details TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)')

    # ── Auto-sanitize existing historical after-hours scans to absent ──
    try:
        c.execute("UPDATE attendance SET status = 'absent' WHERE time_in IS NOT NULL AND (time_in < '06:00:00' OR time_in > '17:00:00')")
    except Exception:
        pass

    conn.commit()
    conn.close()
    _db_is_initialized = True
    engine_name = "Render PostgreSQL" if IS_POSTGRES else "Local SQLite"
    print(f"Database initialized successfully [{engine_name}]")


# ============================================
# USER MANAGEMENT
# ============================================

def create_user(username, email, password, full_name, role='user'):
    """Create a new user"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        password_hash = hash_password(password)

        if conn.is_postgres:
            c.execute('''
                INSERT INTO users (username, email, password_hash, full_name, role)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (username, email, password_hash, full_name, role))
            res = c.fetchone()
            user_id = res['id'] if res else None
        else:
            c.execute('''
                INSERT INTO users (username, email, password_hash, full_name, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, full_name, role))
            user_id = c.lastrowid

        conn.commit()
        conn.close()
        return user_id
    except Exception as e:
        err = str(e).lower()
        if 'username' in err:
            return None, 'Username already exists'
        elif 'email' in err:
            return None, 'Email already registered'
        return None, str(e)


def get_user_by_username(username):
    """Get user by username"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    return user


def get_user_by_email(email):
    """Get user by email"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user


def delete_user_completely(user_id, admin_id=None):
    """
    Completely and permanently delete a user and all their associated records:
    - attendance records
    - email notifications
    - attendance reports
    - user account and facial embeddings
    Also records an audit log entry.
    Cannot delete users with role == 'admin'.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # 1. Fetch user to verify existence and protect admin
        c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        if not user:
            conn.close()
            return False, "User not found"
        
        user_dict = dict(user)
        if user_dict.get('role') == 'admin':
            conn.close()
            return False, "Cannot delete an Administrator account"

        # 2. Atomic deletion across all tables
        c.execute('DELETE FROM attendance WHERE user_id = ?', (user_id,))
        c.execute('DELETE FROM email_notifications WHERE user_id = ?', (user_id,))
        c.execute('DELETE FROM attendance_reports WHERE user_id = ?', (user_id,))
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

        # 3. Log audit event
        try:
            log_audit(
                user_id=admin_id,
                action='delete_user',
                resource_type='users',
                resource_id=user_id,
                details=f"Permanently deleted user '{user_dict.get('username')}' ({user_dict.get('full_name')}) and all biometric/attendance history."
            )
        except Exception:
            pass

        return True, f"User '{user_dict.get('username')}' deleted successfully"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)


def authenticate_user(username, password):
    """Authenticate user with username and password"""
    user = get_user_by_username(username)
    if not user:
        return None
    if verify_password(user['password_hash'], password):
        return user
    return None


def update_user_embedding(user_id, embedding_vector):
    """Update user's face embedding"""
    embedding_str = json.dumps(embedding_vector.tolist())
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET embedding = ? WHERE id = ?', (embedding_str, user_id))
    conn.commit()
    conn.close()


def get_all_users():
    """Get all active users"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, email, full_name, role, status, embedding FROM users WHERE status = 'active'")
    users = c.fetchall()
    conn.close()
    return users


def get_currently_on_duty_count():
    """
    Real-time Live Working Employees Calculation:
    Returns (count, status_message, is_shift_active).
    Enforces 06:00 AM - 05:00 PM IST Mon-Sat shift window:
    - If current time < 06:00:00 (Office unopened) -> 0
    - If current time > 17:00:00 (Shift completed for the day / 0s remaining) -> 0
    - If Sunday (Weekly off) -> 0
    - Otherwise -> Count of non-admin active users who checked in today (present/late/half_day).
    """
    now_dt = datetime.now(IST)

    # Sunday weekly off
    if now_dt.weekday() == 6:
        return 0, 'Office Closed (Sunday Off)', False

    now_time = now_dt.strftime('%H:%M:%S')
    today_date = now_dt.strftime('%Y-%m-%d')

    if now_time < '06:00:00':
        return 0, 'Shift Not Started (Opens 06:00 AM IST)', False

    if now_time > '17:00:00':
        return 0, 'Shift Completed (5:00 PM Off)', False

    # Shift in progress! Query live database
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(DISTINCT a.user_id) as cnt
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE a.date = ?
          AND a.status IN ('present', 'late', 'half_day')
          AND u.role != 'admin'
          AND u.status = 'active'
    ''', (today_date,))
    row = c.fetchone()
    conn.close()

    cnt = row['cnt'] if row else 0
    return cnt, 'Shift In Progress (Live On-Duty)', True


def get_all_users_admin():
    """Get all users for administrator management."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, username, email, full_name, role, status, is_verified, embedding, profile_picture, created_at, updated_at
        FROM users
        ORDER BY (CASE WHEN role = 'admin' THEN 0 ELSE 1 END), created_at DESC, id DESC
    ''')
    users = c.fetchall()
    conn.close()

    cleaned = []
    for u in users:
        d = dict(u)
        if isinstance(d.get('created_at'), datetime):
            d['created_at'] = d['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(d.get('updated_at'), datetime):
            d['updated_at'] = d['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        cleaned.append(d)
    return cleaned


def ensure_default_admin():
    """Create the default administrator account from environment variables if needed."""
    admin_username = os.getenv('ADMIN_USERNAME', 'admin').strip()
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@gmail.com').strip().lower()
    admin_password = os.getenv('ADMIN_PASSWORD', 'Admin12345')
    admin_full_name = os.getenv('ADMIN_FULL_NAME', 'System Administrator').strip()

    existing_admin = get_user_by_username(admin_username)
    if existing_admin:
        if existing_admin.get('role') != 'admin':
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                UPDATE users
                SET role = 'admin', status = 'active', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (existing_admin['id'],))
            conn.commit()
            conn.close()
        return

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role, status, is_verified)
        VALUES (?, ?, ?, ?, 'admin', 'active', 1)
    ''', (admin_username, admin_email, hash_password(admin_password), admin_full_name))
    conn.commit()
    conn.close()


def update_user_profile_picture(user_id, profile_picture):
    """Update user profile picture (base64 data URL or path)"""
    conn = get_db_connection()
    c = conn.cursor()
    if conn.is_postgres:
        c.execute('''
            UPDATE users
            SET profile_picture = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (profile_picture, user_id))
    else:
        c.execute('''
            UPDATE users
            SET profile_picture = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (profile_picture, user_id))
    conn.commit()
    conn.close()
    return True


# ============================================
# ATTENDANCE MANAGEMENT
# ============================================

def _normalize_attendance_datetime(attendance_date=None, attendance_time=None):
    """Normalize attendance inputs to a timezone-aware UTC datetime plus date/time strings."""
    if attendance_date is None:
        normalized_datetime = datetime.now(IST)
    elif isinstance(attendance_date, datetime):
        normalized_datetime = attendance_date.astimezone(IST)
    elif attendance_time:
        normalized_datetime = datetime.strptime(
            f'{attendance_date} {attendance_time}', '%Y-%m-%d %H:%M:%S'
        ).replace(tzinfo=IST)
    else:
        normalized_datetime = datetime.strptime(attendance_date, '%Y-%m-%d').replace(tzinfo=IST)

    return (
        normalized_datetime,
        normalized_datetime.strftime('%Y-%m-%d'),
        normalized_datetime.strftime('%H:%M:%S')
    )


def get_latest_attendance_for_user(user_id):
    """Get the latest attendance row for a user based on stored date/time."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT *
        FROM attendance
        WHERE user_id = ?
        ORDER BY date DESC, time_in DESC, created_at DESC
        LIMIT 1
    ''', (user_id,))
    record = c.fetchone()
    conn.close()
    return record


def mark_attendance(user_id, attendance_date=None, attendance_time=None, status=None):
    """
    Corporate biometric attendance device logic.

    Shift:     09:00 AM - 05:00 PM IST (8 hour shift)
    Grace:     15 minutes (on-time cutoff = 09:15 AM)
    Window:    06:00 AM - 05:00 PM IST (device locks at shift end)

    Status Rules:
      06:00 - 09:15  ->  present    (on-time)
      09:16 - 13:00  ->  late       (late arrival, full day counted)
      13:01 - 17:00  ->  half_day   (less than half shift remaining)
      After 17:00    ->  REJECTED   (device locked, user is already absent)
      Before 06:00   ->  REJECTED   (office not open)
    """
    normalized_datetime, attendance_date, attendance_time = _normalize_attendance_datetime(
        attendance_date, attendance_time
    )

    conn = get_db_connection()
    c = conn.cursor()

    # Check for existing record today (present/late/half_day OR absent)
    c.execute('SELECT id, status FROM attendance WHERE user_id = ? AND date = ?', (user_id, attendance_date))
    existing = c.fetchone()

    if existing:
        existing_status = existing.get('status', '')
        conn.close()
        if existing_status == 'absent':
            return False, 'already_absent'
        return False, 'duplicate'

    # --- Corporate device status determination ---
    if not status:
        SHIFT_START   = '09:00:00'
        SHIFT_END     = '17:00:00'   # 5:00 PM
        GRACE_CUTOFF  = '09:15:00'   # 9:15 AM (15-min grace)
        HALFDAY_CUTOFF = '13:00:00'  # 1:00 PM
        WINDOW_OPEN   = '06:00:00'   # 6:00 AM earliest

        # REJECT: Sunday is weekly off (Mon-Sat 6-day work week)
        dt_obj = datetime.strptime(attendance_date, '%Y-%m-%d')
        if dt_obj.weekday() == 6:  # 6 = Sunday
            conn.close()
            return False, 'office_closed_sunday'

        # REJECT: before office opens
        if attendance_time < WINDOW_OPEN:
            conn.close()
            return False, 'office_closed_early'

        # REJECT: after shift end — device locked
        if attendance_time > SHIFT_END:
            conn.close()
            return False, 'office_closed'

        # Determine status
        if attendance_time > HALFDAY_CUTOFF:
            status = 'half_day'
        elif attendance_time > GRACE_CUTOFF:
            status = 'late'
        else:
            status = 'present'

    # Insert attendance record
    c.execute('''
        INSERT INTO attendance (user_id, date, time_in, status)
        VALUES (?, ?, ?, ?)
    ''', (user_id, attendance_date, attendance_time, status))
    conn.commit()
    conn.close()
    return True, status


def resolve_attendance_status(raw_status, time_in):
    """Canonical 9-to-5 status resolution for any stored record"""
    if raw_status == 'absent' or not time_in:
        return 'absent'
    if time_in < '06:00:00' or time_in > '17:00:00':
        return 'absent'
    if raw_status in ('half_day', 'late'):
        return raw_status
    if time_in <= '09:15:00':
        return 'present'
    if time_in <= '13:00:00':
        return 'late'
    if time_in <= '17:00:00':
        return 'half_day'
    return 'absent'


def get_attendance_by_user(user_id, limit=50):
    """Get attendance records for a user with canonical status."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT a.*, u.username, u.email, u.full_name
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE a.user_id = ?
        ORDER BY a.date DESC
        LIMIT ?
    ''', (user_id, limit))
    records = c.fetchall()
    conn.close()
    
    cleaned = []
    for r in records:
        d = dict(r)
        d['status'] = resolve_attendance_status(d.get('status'), d.get('time_in'))
        cleaned.append(d)
    return cleaned


def get_attendance_records(start_date=None, end_date=None):
    """Get all attendance records with optional date filter and canonical status."""
    conn = get_db_connection()
    c = conn.cursor()
    
    if start_date and end_date:
        c.execute('''
            SELECT a.*, u.username, u.email, u.full_name
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            WHERE a.date BETWEEN ? AND ?
            ORDER BY a.date DESC, a.time_in DESC
        ''', (start_date, end_date))
    else:
        c.execute('''
            SELECT a.*, u.username, u.email, u.full_name
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.date DESC, a.time_in DESC
        ''')
    
    records = c.fetchall()
    conn.close()
    
    cleaned = []
    for r in records:
        d = dict(r)
        d['status'] = resolve_attendance_status(d.get('status'), d.get('time_in'))
        cleaned.append(d)
    return cleaned


def get_all_attendance_admin(limit=500):
    """Get all attendance records for administrator views with canonical status."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT a.*, u.username, u.email, u.full_name, u.role, u.profile_picture
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.date DESC, a.time_in DESC, a.created_at DESC
        LIMIT ?
    ''', (limit,))
    records = c.fetchall()
    conn.close()
    
    cleaned = []
    for r in records:
        d = dict(r)
        d['status'] = resolve_attendance_status(d.get('status'), d.get('time_in'))
        if isinstance(d.get('date'), (datetime,)):
            d['date'] = d['date'].strftime('%Y-%m-%d')
        if hasattr(d.get('date'), 'strftime'):
            d['date'] = d['date'].strftime('%Y-%m-%d')
        if hasattr(d.get('time_in'), 'strftime'):
            d['time_in'] = d['time_in'].strftime('%H:%M:%S')
        cleaned.append(d)
    return cleaned


def _format_db_date(value):
    """Return a database date value as an ISO date string."""
    if value is None:
        return None
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d')
    return str(value)[:10]


def _format_db_time(value):
    """Return a database time value as HH:MM:SS."""
    if value is None:
        return None
    if hasattr(value, 'strftime'):
        return value.strftime('%H:%M:%S')
    return str(value)[:8]


def _attendance_status_for_admin(raw_status, time_in, record_date, today_date, now_time):
    """Resolve a record, including users that have no attendance row yet.

    A missing record on a previous working day is absent. A missing record on
    the current day remains pending until the shift closes, which prevents the
    dashboard from incorrectly calling someone absent at 9 AM.
    """
    resolved = resolve_attendance_status(raw_status, time_in)
    if resolved != 'absent':
        return resolved

    if raw_status == 'absent' or time_in:
        return 'absent'

    if record_date < today_date or (record_date == today_date and now_time >= '17:00:00'):
        return 'absent'
    return 'pending'


def get_admin_today_attendance(attendance_date=None):
    """Return one live status row for every active non-admin user.

    This is intentionally driven from users with a LEFT JOIN to attendance.
    Therefore a user who has not checked in still appears as pending/absent.
    """
    now_dt = datetime.now(IST)
    today_date = attendance_date or now_dt.strftime('%Y-%m-%d')
    now_time = now_dt.strftime('%H:%M:%S')

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT
            u.id AS user_id,
            u.username,
            u.email,
            u.full_name,
            u.role,
            u.status AS user_status,
            CASE WHEN u.embedding IS NOT NULL AND u.embedding <> '' THEN 1 ELSE 0 END AS is_enrolled,
            a.id AS attendance_id,
            a.date AS attendance_date,
            a.time_in,
            a.time_out,
            a.status AS raw_status,
            a.notes,
            a.marked_by,
            a.created_at,
            a.updated_at
        FROM users u
        LEFT JOIN attendance a
            ON a.user_id = u.id AND a.date = ?
        WHERE u.status = 'active' AND u.role <> 'admin'
        ORDER BY LOWER(COALESCE(u.full_name, u.username)), u.id
    ''', (today_date,))
    rows = c.fetchall()
    conn.close()

    records = []
    counts = {'present': 0, 'late': 0, 'half_day': 0, 'absent': 0, 'pending': 0}
    for row in rows:
        d = dict(row)
        row_date = _format_db_date(d.get('attendance_date')) or today_date
        time_in = _format_db_time(d.get('time_in'))
        status = _attendance_status_for_admin(
            d.get('raw_status'), time_in, row_date, today_date, now_time
        )
        counts[status] = counts.get(status, 0) + 1
        records.append({
            'user_id': d.get('user_id'),
            'username': d.get('username'),
            'full_name': d.get('full_name') or d.get('username'),
            'email': d.get('email'),
            'role': d.get('role'),
            'is_enrolled': bool(d.get('is_enrolled')),
            'attendance_id': d.get('attendance_id'),
            'date': today_date,
            'time_in': time_in,
            'time_out': _format_db_time(d.get('time_out')),
            'status': status,
            'raw_status': d.get('raw_status'),
            'notes': d.get('notes'),
            'marked_by': d.get('marked_by'),
        })

    return {
        'date': today_date,
        'records': records,
        'counts': counts,
        'total_users': len(records),
        'is_shift_closed': now_time >= '17:00:00',
        'generated_at': now_dt.isoformat(),
    }


def get_admin_user_attendance_history(user_id, start_date=None, end_date=None,
                                      status_filter=None, page=1, page_size=31):
    """Return a paginated history that includes implicit absent working days."""
    today = datetime.now(IST).date()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, username, email, full_name, role, status,
               embedding, created_at
        FROM users
        WHERE id = ?
    ''', (user_id,))
    user = c.fetchone()
    if not user or user.get('role') == 'admin':
        conn.close()
        return None

    user = dict(user)
    created_value = user.get('created_at')
    if hasattr(created_value, 'date'):
        created_date = created_value.date()
    else:
        try:
            created_date = datetime.strptime(str(created_value)[:10], '%Y-%m-%d').date()
        except (TypeError, ValueError):
            created_date = today

    def parse_date(value, fallback):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date() if value else fallback
        except (TypeError, ValueError):
            return fallback

    start = parse_date(start_date, created_date)
    end = min(parse_date(end_date, today), today)
    if start < created_date:
        start = created_date
    if start > end:
        # Invalid/future ranges resolve to the latest valid date instead of
        # generating future "pending" attendance rows.
        start = end

    c.execute('''
        SELECT a.date, a.time_in, a.time_out, a.status, a.notes,
               a.marked_by, a.id AS attendance_id
        FROM attendance a
        WHERE a.user_id = ? AND a.date BETWEEN ? AND ?
        ORDER BY a.date DESC
    ''', (user_id, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))
    attendance_rows = c.fetchall()
    conn.close()

    by_date = {}
    for row in attendance_rows:
        d = dict(row)
        date_text = _format_db_date(d.get('date'))
        by_date[date_text] = d

    now_dt = datetime.now(IST)
    today_text = today.strftime('%Y-%m-%d')
    now_time = now_dt.strftime('%H:%M:%S')
    all_records = []
    cursor_date = start
    while cursor_date <= end:
        # Existing business policy is Monday-Saturday; Sunday is weekly off.
        if cursor_date.weekday() != 6:
            date_text = cursor_date.strftime('%Y-%m-%d')
            source = by_date.get(date_text)
            raw_status = source.get('status') if source else None
            time_in = _format_db_time(source.get('time_in')) if source else None
            status = _attendance_status_for_admin(
                raw_status, time_in, date_text, today_text, now_time
            )
            all_records.append({
                'attendance_id': source.get('attendance_id') if source else None,
                'user_id': user_id,
                'date': date_text,
                'time_in': time_in,
                'time_out': _format_db_time(source.get('time_out')) if source else None,
                'status': status,
                'raw_status': raw_status,
                'notes': source.get('notes') if source else None,
                'marked_by': source.get('marked_by') if source else 'auto_absent',
            })
        cursor_date += timedelta(days=1)

    summary = {'present': 0, 'late': 0, 'half_day': 0, 'absent': 0, 'pending': 0}
    for record in all_records:
        summary[record['status']] = summary.get(record['status'], 0) + 1

    if status_filter and status_filter in summary:
        all_records = [r for r in all_records if r['status'] == status_filter]

    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(100, max(10, int(page_size)))
    except (TypeError, ValueError):
        page_size = 31

    total = len(all_records)
    start_index = (page - 1) * page_size
    return {
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user.get('full_name') or user.get('username'),
            'email': user.get('email'),
            'is_enrolled': bool(user.get('embedding')),
        },
        'records': all_records[start_index:start_index + page_size],
        'summary': summary,
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': max(1, (total + page_size - 1) // page_size),
        'start_date': start.strftime('%Y-%m-%d'),
        'end_date': end.strftime('%Y-%m-%d'),
    }


def get_attendance_today():
    """Get today's attendance records with canonical status."""
    today = datetime.now(IST).strftime('%Y-%m-%d')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT a.*, u.username, u.email, u.full_name
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE a.date = ?
        ORDER BY a.time_in DESC
    ''', (today,))
    records = c.fetchall()
    conn.close()
    
    cleaned = []
    for r in records:
        d = dict(r)
        d['status'] = resolve_attendance_status(d.get('status'), d.get('time_in'))
        cleaned.append(d)
    return cleaned


def check_and_mark_absent(user_id, date):
    """Mark user as absent if not marked by end of day (Mon-Sat only, Sunday is off)"""
    try:
        if datetime.strptime(date, '%Y-%m-%d').weekday() == 6:
            return False  # Sunday is off day, never mark absent
    except Exception:
        pass

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM attendance WHERE user_id = ? AND date = ?', (user_id, date))
    existing = c.fetchone()
    
    if not existing:
        c.execute('''
            INSERT INTO attendance (user_id, date, status)
            VALUES (?, ?, 'absent')
        ''', (user_id, date))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False


# ============================================
# REPORTING
# ============================================

def generate_daily_report(user_id, report_date):
    """Generate daily attendance report"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT COUNT(*) as total_present
        FROM attendance
        WHERE user_id = ? AND date = ? AND status = 'present'
    ''', (user_id, report_date))
    present_row = c.fetchone()
    present = present_row['total_present'] if present_row else 0
    
    c.execute('''
        SELECT COUNT(*) as total_late
        FROM attendance
        WHERE user_id = ? AND date = ? AND status = 'late'
    ''', (user_id, report_date))
    late_row = c.fetchone()
    late = late_row['total_late'] if late_row else 0
    
    report_data = {
        'user_id': user_id,
        'date': report_date,
        'present': present,
        'late': late,
        'absent': 1 - (present or late),
        'generated_at': datetime.now(IST).isoformat()
    }

    if conn.is_postgres:
        c.execute('''
            INSERT INTO attendance_reports 
            (user_id, report_type, report_date, total_present, total_late, report_data)
            VALUES (%s, 'daily', %s, %s, %s, %s)
            ON CONFLICT (user_id, report_date) 
            DO UPDATE SET total_present = EXCLUDED.total_present, total_late = EXCLUDED.total_late, report_data = EXCLUDED.report_data
        ''', (user_id, report_date, present, late, json.dumps(report_data)))
    else:
        c.execute('''
            INSERT OR REPLACE INTO attendance_reports 
            (user_id, report_type, report_date, total_present, total_late, report_data)
            VALUES (?, 'daily', ?, ?, ?, ?)
        ''', (user_id, report_date, present, late, json.dumps(report_data)))
    
    conn.commit()
    conn.close()
    return report_data


def get_user_monthly_summary(user_id, year, month):
    """Get user's monthly attendance summary"""
    conn = get_db_connection()
    c = conn.cursor()
    
    date_pattern = f'{year:04d}-{month:02d}-%'
    
    c.execute('''
        SELECT 
            COUNT(CASE WHEN status = 'present' THEN 1 END) as total_present,
            COUNT(CASE WHEN status = 'late' THEN 1 END) as total_late,
            COUNT(CASE WHEN status = 'absent' THEN 1 END) as total_absent,
            COUNT(*) as total_days
        FROM attendance
        WHERE user_id = ? AND date LIKE ?
    ''', (user_id, date_pattern))
    
    result = c.fetchone()
    conn.close()
    
    return {
        'user_id': user_id,
        'year': year,
        'month': month,
        'present': result['total_present'] if result else 0,
        'late': result['total_late'] if result else 0,
        'absent': result['total_absent'] if result else 0,
        'total_days': result['total_days'] if result else 0
    }


# ============================================
# AUDIT LOGGING
# ============================================

def log_audit(user_id, action, resource_type=None, resource_id=None, details=None, ip_address=None):
    """Log user actions for audit trail"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, action, resource_type, resource_id, details, ip_address))
    conn.commit()
    conn.close()


# ============================================
# EMAIL NOTIFICATION TRACKING
# ============================================

def log_email_notification(user_id, email_type, recipient_email, subject):
    """Log email notification attempt"""
    conn = get_db_connection()
    c = conn.cursor()
    if conn.is_postgres:
        c.execute('''
            INSERT INTO email_notifications (user_id, email_type, recipient_email, subject)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (user_id, email_type, recipient_email, subject))
        res = c.fetchone()
        notification_id = res['id'] if res else None
    else:
        c.execute('''
            INSERT INTO email_notifications (user_id, email_type, recipient_email, subject)
            VALUES (?, ?, ?, ?)
        ''', (user_id, email_type, recipient_email, subject))
        notification_id = c.lastrowid
    
    conn.commit()
    conn.close()
    return notification_id


def update_email_notification_status(notification_id, status, error_message=None):
    """Update email notification status"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE email_notifications
        SET status = ?, error_message = ?, sent_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, error_message, notification_id))
    conn.commit()
    conn.close()


def get_pending_emails():
    """Get pending email notifications"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM email_notifications
        WHERE status = 'pending'
        ORDER BY created_at ASC
    ''')
    records = c.fetchall()
    conn.close()
    return records


def update_user_password(user_id, new_password):
    """Update user password"""
    password_hash = hash_password(new_password)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE users
        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (password_hash, user_id))
    conn.commit()
    conn.close()
    return c.rowcount > 0
