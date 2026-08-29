"""
Unit tests for registration OTP flow (no live SMTP required).
Run from repo root:
  python -m unittest tests.test_otp_registration -v
"""

import os
import sys
import unittest
from datetime import timedelta
from unittest.mock import patch

# Ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-otp')
os.environ.setdefault('SMTP_ENABLED', 'false')
os.environ.setdefault('SCHEDULER_ENABLED', 'false')
# Prefer /tmp for sandbox filesystem reliability
TEST_DB = os.environ.get('TEST_DB_PATH', '/tmp/test_otp_attendance.db')
os.environ['DB_PATH'] = TEST_DB
os.environ.pop('DATABASE_URL', None)
if os.path.exists(TEST_DB):
    try:
        os.remove(TEST_DB)
    except OSError:
        pass


class OtpHelpersTest(unittest.TestCase):
    def test_generate_otp_is_six_digits(self):
        from app.routes.auth import _generate_otp
        for _ in range(50):
            otp = _generate_otp()
            self.assertTrue(otp.isdigit())
            self.assertEqual(len(otp), 6)

    def test_otp_hash_not_plaintext(self):
        from app.models.db import hash_otp
        otp = '123456'
        h = hash_otp(otp)
        self.assertNotEqual(h, otp)
        self.assertEqual(hash_otp(otp), h)
        self.assertNotEqual(hash_otp('654321'), h)

    def test_mask_email(self):
        from app.routes.auth import _mask_email
        masked = _mask_email('suprabh.sharma@gmail.com')
        self.assertIn('@gmail.com', masked)
        self.assertNotIn('suprabh.sharma', masked)
        self.assertTrue(masked.startswith('s'))


class PendingVerificationDbTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except OSError:
                pass
        import app.models.db as dbmod
        dbmod._db_is_initialized = False
        dbmod.IS_POSTGRES = False
        dbmod.DATABASE_URL = ''
        dbmod.DB_PATH = os.path.abspath(TEST_DB)
        os.makedirs(os.path.dirname(dbmod.DB_PATH) or '.', exist_ok=True)
        dbmod.init_db(force=True)

    def setUp(self):
        import sqlite3
        import time
        from app.models.db import DB_PATH
        # Direct connection with timeout to avoid leftover locks between tests
        for _ in range(5):
            try:
                raw = sqlite3.connect(DB_PATH, timeout=10)
                raw.execute('PRAGMA busy_timeout = 10000')
                raw.execute('DELETE FROM pending_email_verifications')
                raw.execute("DELETE FROM users WHERE role != 'admin'")
                raw.commit()
                raw.close()
                break
            except sqlite3.OperationalError:
                time.sleep(0.3)

    def test_create_and_get_pending(self):
        from app.models.db import (
            create_or_replace_pending_verification,
            get_active_pending_by_email,
            hash_password,
            hash_otp,
            _utc_now,
        )
        expires = _utc_now() + timedelta(minutes=10)
        create_or_replace_pending_verification(
            email='testuser@gmail.com',
            full_name='Test User',
            username='Test User',
            password_hash=hash_password('Password1'),
            otp_hash=hash_otp('112233'),
            expires_at=expires,
        )
        row = get_active_pending_by_email('testuser@gmail.com')
        self.assertIsNotNone(row)
        self.assertEqual(row['email'], 'testuser@gmail.com')
        self.assertEqual(row['is_used'], 0)
        self.assertEqual(row['otp_hash'], hash_otp('112233'))

    def test_resend_invalidates_old_otp_hash(self):
        from app.models.db import (
            create_or_replace_pending_verification,
            get_active_pending_by_email,
            update_pending_resend,
            hash_password,
            hash_otp,
            _utc_now,
        )
        expires = _utc_now() + timedelta(minutes=10)
        create_or_replace_pending_verification(
            email='resend@gmail.com',
            full_name='Resend User',
            username='Resend User',
            password_hash=hash_password('Password1'),
            otp_hash=hash_otp('111111'),
            expires_at=expires,
        )
        pending = get_active_pending_by_email('resend@gmail.com')
        self.assertTrue(
            update_pending_resend(
                pending['id'],
                hash_otp('222222'),
                _utc_now() + timedelta(minutes=10),
                1,
            )
        )
        pending2 = get_active_pending_by_email('resend@gmail.com')
        self.assertEqual(pending2['otp_hash'], hash_otp('222222'))
        self.assertNotEqual(pending2['otp_hash'], hash_otp('111111'))
        self.assertEqual(int(pending2['resend_count']), 1)
        self.assertEqual(int(pending2['attempt_count']), 0)

    def test_single_use_after_mark(self):
        from app.models.db import (
            create_or_replace_pending_verification,
            get_active_pending_by_email,
            mark_pending_used,
            hash_password,
            hash_otp,
            _utc_now,
        )
        expires = _utc_now() + timedelta(minutes=10)
        create_or_replace_pending_verification(
            email='once@gmail.com',
            full_name='Once User',
            username='Once User',
            password_hash=hash_password('Password1'),
            otp_hash=hash_otp('333333'),
            expires_at=expires,
        )
        pending = get_active_pending_by_email('once@gmail.com')
        mark_pending_used(pending['id'])
        self.assertIsNone(get_active_pending_by_email('once@gmail.com'))

    def test_max_attempts_counter(self):
        from app.models.db import (
            create_or_replace_pending_verification,
            get_active_pending_by_email,
            increment_pending_attempt,
            hash_password,
            hash_otp,
            _utc_now,
        )
        expires = _utc_now() + timedelta(minutes=10)
        create_or_replace_pending_verification(
            email='attempts@gmail.com',
            full_name='Attempts User',
            username='Attempts User',
            password_hash=hash_password('Password1'),
            otp_hash=hash_otp('444444'),
            expires_at=expires,
        )
        pending = get_active_pending_by_email('attempts@gmail.com')
        for expected in range(1, 6):
            count = increment_pending_attempt(pending['id'])
            self.assertEqual(count, expected)

    def test_create_user_with_prehashed_and_verified(self):
        from app.models.db import create_user, get_user_by_email, hash_password, verify_password
        ph = hash_password('SecurePass9')
        uid = create_user(
            username='Verified Person',
            email='verified.person@gmail.com',
            full_name='Verified Person',
            role='user',
            is_verified=1,
            password_hash=ph,
        )
        self.assertIsInstance(uid, int)
        user = get_user_by_email('verified.person@gmail.com')
        self.assertEqual(int(user['is_verified']), 1)
        self.assertTrue(verify_password(user['password_hash'], 'SecurePass9'))
        # Ensure not double-hashed
        self.assertEqual(user['password_hash'], ph)

    def test_duplicate_email_blocked_by_create_user(self):
        from app.models.db import create_user
        create_user(
            username='Dup One',
            email='dup@gmail.com',
            password='Password1',
            full_name='Dup One',
            is_verified=1,
        )
        result = create_user(
            username='Dup Two',
            email='dup@gmail.com',
            password='Password1',
            full_name='Dup Two',
            is_verified=1,
        )
        self.assertIsInstance(result, tuple)
        self.assertIsNone(result[0])

    def test_smtp_failure_does_not_create_account(self):
        """Simulate register path: pending stored, SMTP fails → no users row."""
        from app.models.db import (
            create_or_replace_pending_verification,
            get_user_by_email,
            hash_password,
            hash_otp,
            _utc_now,
        )
        from app.services.email_service import email_service

        email = 'smtpfail@gmail.com'
        expires = _utc_now() + timedelta(minutes=10)
        create_or_replace_pending_verification(
            email=email,
            full_name='Smtp Fail',
            username='Smtp Fail',
            password_hash=hash_password('Password1'),
            otp_hash=hash_otp('555555'),
            expires_at=expires,
        )
        with patch.object(email_service, 'send_registration_otp', return_value=False):
            sent = email_service.send_registration_otp(email, 'Smtp Fail', '555555')
        self.assertFalse(sent)
        self.assertIsNone(get_user_by_email(email))

    def test_successful_verification_creates_user(self):
        from app.models.db import (
            create_or_replace_pending_verification,
            get_active_pending_by_email,
            mark_pending_used,
            create_user,
            get_user_by_email,
            hash_password,
            hash_otp,
            _utc_now,
        )
        email = 'success@gmail.com'
        otp = '666666'
        expires = _utc_now() + timedelta(minutes=10)
        create_or_replace_pending_verification(
            email=email,
            full_name='Success User',
            username='Success User',
            password_hash=hash_password('Password1'),
            otp_hash=hash_otp(otp),
            expires_at=expires,
        )
        pending = get_active_pending_by_email(email)
        self.assertEqual(pending['otp_hash'], hash_otp(otp))
        uid = create_user(
            username=pending['username'],
            email=pending['email'],
            full_name=pending['full_name'],
            is_verified=1,
            password_hash=pending['password_hash'],
        )
        mark_pending_used(pending['id'])
        self.assertIsInstance(uid, int)
        user = get_user_by_email(email)
        self.assertEqual(int(user['is_verified']), 1)
        self.assertIsNone(get_active_pending_by_email(email))

    def test_expired_otp_window(self):
        from app.models.db import (
            create_or_replace_pending_verification,
            get_active_pending_by_email,
            _utc_now,
            _parse_utc,
            hash_password,
            hash_otp,
        )
        email = 'expired@gmail.com'
        past = _utc_now() - timedelta(minutes=1)
        create_or_replace_pending_verification(
            email=email,
            full_name='Expired User',
            username='Expired User',
            password_hash=hash_password('Password1'),
            otp_hash=hash_otp('777777'),
            expires_at=past,
        )
        pending = get_active_pending_by_email(email)
        expires_at = _parse_utc(pending['expires_at'])
        self.assertTrue(_utc_now() > expires_at)


if __name__ == '__main__':
    unittest.main()
