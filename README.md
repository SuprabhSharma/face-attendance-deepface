# 🎯 Face Recognition Attendance System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10.13-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0.0-black?style=for-the-badge&logo=flask)
![DeepFace](https://img.shields.io/badge/DeepFace-0.0.83-orange?style=for-the-badge)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.12.0-FF6F00?style=for-the-badge&logo=tensorflow)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite)
![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**An AI-powered, browser-based attendance management system using real-time face recognition.**  
No hardware required. Works entirely through a webcam.

[🚀 Live Demo](https://face-attendance-deepface.onrender.com) · [📖 API Docs](#-api-reference) · [🐛 Report Bug](https://github.com/SuprabhSharma/face-attendance-deepface/issues) · [✨ Request Feature](https://github.com/SuprabhSharma/face-attendance-deepface/issues)

</div>

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [System Architecture](#-system-architecture)
3. [Tech Stack](#-tech-stack)
4. [Functional Requirements](#-functional-requirements)
5. [Non-Functional Requirements](#-non-functional-requirements)
6. [Database Schema](#-database-schema)
7. [API Reference](#-api-reference)
8. [Face Recognition Design](#-face-recognition-design)
9. [Project Structure](#-project-structure)
10. [Getting Started (Local)](#-getting-started-local)
11. [Deployment (Render Free Plan)](#-deployment-render-free-plan)
12. [Environment Variables](#-environment-variables)
13. [Security Considerations](#-security-considerations)
14. [Known Limitations](#-known-limitations)
15. [Contributing](#-contributing)

---

## 📌 Project Overview

### Purpose
The Face Recognition Attendance System replaces manual attendance processes with an automated, AI-based solution. Users register their face once via webcam, and from then on, attendance is marked by simply looking at the camera — no ID cards, no sign-in sheets, no manual entry.

### Problem Statement
Traditional attendance systems are:
- Prone to **buddy punching** (one person marking attendance for another)
- **Time-consuming** for large groups
- **Error-prone** with manual records
- Difficult to generate **real-time reports**

### Solution
This system uses the **SFace** face recognition model (lightweight, 28MB) to generate a unique face embedding for each user. On each attendance scan, the live face is compared against stored embeddings. A match within a configured L2 distance threshold marks attendance automatically.

### Scope
| In Scope | Out of Scope |
|---|---|
| Web-based face registration | Mobile native app |
| Real-time face recognition | Multi-camera support |
| Attendance tracking & reports | Payroll integration |
| Admin user management | Physical access control |
| Email notifications | SMS notifications |
| Role-based access control | LDAP / SSO integration |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                     │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ webcam   │→ │ canvas API   │→ │ Base64 JPEG image  │    │
│  └──────────┘  └──────────────┘  └────────┬───────────┘    │
└───────────────────────────────────────────┼─────────────────┘
                                            │ HTTPS POST /api/...
┌───────────────────────────────────────────▼─────────────────┐
│                     FLASK APPLICATION                        │
│                                                             │
│  ┌─────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  auth.py    │  │     api.py       │  │   views.py    │  │
│  │  (login /   │  │  (register face/ │  │  (page        │  │
│  │   register) │  │   mark attend.)  │  │   routing)    │  │
│  └─────────────┘  └────────┬─────────┘  └───────────────┘  │
│                            │                                │
│                   ┌────────▼────────┐                       │
│                   │  face_service   │                       │
│                   │  (SFace model)  │                       │
│                   │  DeepFace API   │                       │
│                   └────────┬────────┘                       │
│                            │                                │
│                   ┌────────▼────────┐  ┌─────────────────┐ │
│                   │    db.py        │  │  scheduler.py   │ │
│                   │  (SQLite CRUD)  │  │  (APScheduler)  │ │
│                   └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │   SQLite DB     │
                   │ attendance.db   │
                   └─────────────────┘
```

### Request Flow — Mark Attendance
```
User clicks "Scan Face"
    → Webcam frame captured as Base64 JPEG
    → POST /api/recognize-face
    → base64_to_cv2() converts image
    → DeepFace.represent() generates SFace embedding (128-dim vector)
    → L2 distance compared against all enrolled embeddings
    → Best match found within threshold (12.0)?
        YES → mark_attendance() → return success + name
        NO  → return "face not recognized"
```

---

## 🛠 Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Language** | Python | 3.10.13 | Core backend |
| **Framework** | Flask | 3.0.0 | Web server & routing |
| **Auth** | Flask-Login | 0.6.3 | Session management |
| **ORM** | SQLAlchemy | 2.0.29 | DB abstraction |
| **Database** | SQLite | 3 | Data persistence |
| **AI Model** | DeepFace | 0.0.83 | Face recognition engine |
| **Face Model** | SFace | 28MB | Embedding generation |
| **ML Runtime** | TensorFlow | 2.12.0 | Model inference |
| **Image Proc.** | OpenCV (headless) | 4.8.1.78 | Frame processing |
| **Scheduler** | APScheduler | 3.10.4 | Automated tasks |
| **Server** | Gunicorn | 21.2.0 | WSGI production server |
| **Frontend** | Bootstrap 5 | 5.3.0 | Responsive UI |
| **Deployment** | Render | Free Plan | Cloud hosting |

---

## ✅ Functional Requirements

### FR-01: User Registration (Account)
- Users can register with: full name, username, email, password
- Username must be unique (3–30 alphanumeric chars)
- Password must be ≥ 8 chars with complexity requirements
- Duplicate email/username rejected with clear error message

### FR-02: Face Registration
- Logged-in user can register their face via webcam
- System captures a frame and generates a 128-dim SFace embedding
- Embedding saved to the user's record in the database
- User can re-register to update their face (e.g., different lighting)
- System prevents registering a face already belonging to another user

### FR-03: Mark Attendance
- Any page visitor can scan face (no login required at scan page)
- System captures frame → generates embedding → finds closest match
- If L2 distance ≤ threshold (default 12.0): attendance marked
- Attendance marked once per 24-hour window per user
- Returns: user name, timestamp (IST), status (present/late/absent)
- Sends confirmation email via EmailJS

### FR-04: Attendance Rules
| Status | Condition |
|---|---|
| `present` | Marked before 9:00 AM IST |
| `late` | Marked after 9:00 AM IST |
| `absent` | Not marked by end of day (auto-marked by scheduler) |
| `duplicate` | Second attempt within 24 hours |

### FR-05: Reports
- Users view their own attendance history (last 50 records)
- Admin views all users' attendance (up to 1000 records)
- Filter by date range
- Export-ready data format

### FR-06: Admin Panel
- Admin can view all registered users
- Admin can view all attendance records
- Admin account auto-created on first deploy (via env vars)
- Role-based: admin vs user vs manager

### FR-07: Automated Scheduling (APScheduler)
| Job | Schedule | Action |
|---|---|---|
| `mark_end_of_day_absentees` | Daily (end of day) | Marks absent if not attended |
| `send_daily_summaries` | Daily | Sends summary email |
| `generate_monthly_reports` | Monthly | Generates monthly report records |

### FR-08: Email Notifications
- Attendance confirmation email sent via EmailJS on successful scan
- Contains: user name, date, time

---

## ⚡ Non-Functional Requirements

### NFR-01: Performance
| Metric | Target |
|---|---|
| Face embedding generation | < 3 seconds per scan |
| Attendance API response | < 5 seconds end-to-end |
| Page load time | < 2 seconds |
| Concurrent users | 1 (Gunicorn single worker, free plan) |

### NFR-02: Accuracy
| Metric | Value |
|---|---|
| Face model | SFace (InsightFace) |
| Embedding dimensions | 128 |
| Distance metric | L2 (Euclidean) |
| Match threshold | 12.0 (configurable via env) |
| Same-person L2 range | 0 – 10 |
| Different-person L2 range | 13+ |
| Detector backend | OpenCV (fastest for webcam) |
| `enforce_detection` | False (tolerates imperfect lighting) |

### NFR-03: Security
- Passwords hashed with PBKDF2-HMAC-SHA256 (100,000 iterations)
- Session cookies: `HttpOnly`, `Secure` (in production)
- CSRF protection via Flask-WTF
- SQL injection protection via parameterized queries
- Face embeddings stored as JSON blobs (not raw images)
- Audit log for all user actions

### NFR-04: Availability
- Hosted on Render Free Plan (may sleep after 15min inactivity)
- Cold start: ~30-60 seconds on first request after sleep
- No guaranteed uptime SLA on free plan

### NFR-05: Scalability
- Current: SQLite (single-file DB, not concurrent-write safe)
- Upgrade path: Switch `DB_PATH` to PostgreSQL URL + pg8000 driver (already in codebase) for multi-user concurrent writes

---

## 🗄 Database Schema

### `users`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | Unique user ID |
| `username` | TEXT | UNIQUE, NOT NULL | Login username |
| `email` | TEXT | UNIQUE, NOT NULL | Email address |
| `password_hash` | TEXT | NOT NULL | PBKDF2 hashed password |
| `full_name` | TEXT | NOT NULL | Display name |
| `embedding` | BLOB | NULL | JSON-encoded SFace 128-dim vector |
| `role` | TEXT | DEFAULT 'user' | `admin` / `user` / `manager` |
| `status` | TEXT | DEFAULT 'active' | `active` / `inactive` |
| `is_verified` | INTEGER | DEFAULT 0 | Email verification flag |
| `created_at` | TIMESTAMP | DEFAULT NOW | Account creation time |
| `updated_at` | TIMESTAMP | DEFAULT NOW | Last update time |

### `attendance`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | Record ID |
| `user_id` | INTEGER | FK → users.id | Who attended |
| `date` | TEXT | NOT NULL | Date `YYYY-MM-DD` |
| `time_in` | TEXT | | Check-in time `HH:MM:SS` |
| `time_out` | TEXT | | Check-out time (reserved) |
| `status` | TEXT | DEFAULT 'present' | `present`/`late`/`absent`/`half_day` |
| `notes` | TEXT | | Optional notes |
| `marked_by` | TEXT | DEFAULT 'face_recognition' | How it was marked |
| `created_at` | TIMESTAMP | | Record creation time |
| UNIQUE | (user_id, date) | | One record per user per day |

### Other Tables
- `working_hours` — configurable working hours per weekday
- `attendance_reports` — generated daily/weekly/monthly summaries
- `email_notifications` — email send log with status tracking
- `audit_logs` — full audit trail of all user actions

---

## 📡 API Reference

### Authentication Required Endpoints

#### `POST /api/register-user`
Register the logged-in user's face embedding.

**Request:**
```json
{ "image": "<base64-encoded-JPEG>" }
```
**Response (success):**
```json
{ "success": true, "message": "Face registered successfully for Suprabh!" }
```
**Response (error):**
```json
{ "success": false, "message": "No face detected. Ensure good lighting." }
```

---

#### `GET /api/attendance`
Get current user's attendance records (last 50).

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "date": "2026-08-06",
      "name": "Suprabh Sharma",
      "time_in": "09:14:22",
      "time_out": null,
      "status": "late",
      "marked_at": "2026-08-06T09:14:22"
    }
  ]
}
```

---

### Public Endpoints

#### `POST /api/recognize-face`
Identify a face and mark attendance.

**Request:**
```json
{ "image": "<base64-encoded-JPEG>" }
```
**Response (matched):**
```json
{
  "success": true,
  "found": true,
  "user_id": 2,
  "user_name": "Suprabh Sharma",
  "user_email": "suprabh@example.com",
  "status": "present",
  "marked_at": "2026-08-06 09:05:33",
  "message": "Suprabh Sharma marked at 2026-08-06 09:05:33 IST"
}
```
**Response (not matched):**
```json
{
  "success": true,
  "found": false,
  "code": "face_not_recognized",
  "message": "Face not recognized. Look directly at the camera in good lighting and try again."
}
```

---

#### `GET /api/users`
Get list of all users (id + name).

#### `GET /health`
Health check endpoint for Render.
```json
{ "status": "ok" }
```

---

## 🤖 Face Recognition Design

### Model: SFace
- **Full name:** Spherical Face (InsightFace)
- **Model size:** ~28MB (smallest available in DeepFace)
- **Embedding size:** 128 dimensions
- **Designed for:** Edge/mobile real-time recognition
- **Why chosen:** Best balance of speed, size, and accuracy for a free-tier deployment

### Matching Algorithm
```python
# At registration:
embedding = DeepFace.represent(image, model_name="SFace", enforce_detection=False)
# → 128-dim float32 vector saved to DB as JSON

# At attendance scan:
live_embedding = DeepFace.represent(frame, model_name="SFace", ...)
for each enrolled user:
    distance = L2_norm(live_embedding - stored_embedding)
    if distance < best_distance:
        best_match = user

if best_distance <= THRESHOLD (12.0):
    → MATCHED ✅
else:
    → NOT MATCHED ❌
```

### Threshold Guide
| Threshold | Behaviour |
|---|---|
| < 8.0 | Too strict — same person in different lighting may fail |
| **12.0** (default) | ✅ Balanced — recommended |
| > 18.0 | Too loose — risk of false positives |

Set via `FACE_RECOGNITION_THRESHOLD` env var.

---

## 📁 Project Structure

```
face-attendance-deepface/
│
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models/
│   │   └── db.py                # SQLite CRUD + schema init
│   ├── routes/
│   │   ├── api.py               # Face register + recognize APIs
│   │   ├── auth.py              # Login / register / logout
│   │   └── views.py             # Page routing
│   ├── services/
│   │   ├── face_service.py      # SFace embedding + matching
│   │   ├── scheduler.py         # APScheduler jobs
│   │   └── email_service.py     # Email helper
│   ├── templates/
│   │   ├── base.html            # Base layout
│   │   ├── index.html           # Dashboard
│   │   ├── camera.html          # Mark attendance (webcam)
│   │   ├── register.html        # Register face (webcam)
│   │   ├── report.html          # Attendance report
│   │   ├── login.html           # Login page
│   │   ├── admin/               # Admin panel templates
│   │   └── auth/                # Auth templates
│   ├── static/
│   │   ├── css/style.css        # Custom styles
│   │   └── js/main.js           # Camera, toasts, helpers
│   └── utils/
│       ├── helpers.py           # base64_to_cv2 converter
│       └── logging_config.py    # Rotating log handlers
│
├── run.py                       # App entrypoint (Gunicorn)
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render free plan config
├── Dockerfile                   # Docker config (local use)
├── Procfile                     # Gunicorn start command
├── runtime.txt                  # python-3.10.13
└── .env.example                 # Environment variable template
```

---

## 🚀 Getting Started (Local)

### Prerequisites
- Python 3.10.x
- Webcam
- Git

### Setup
```bash
# 1. Clone
git clone https://github.com/SuprabhSharma/face-attendance-deepface.git
cd face-attendance-deepface

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy env file
cp .env.example .env
# Edit .env with your values

# 5. Run
python run.py
```

Visit: `http://localhost:5000`

**Default admin credentials:**
| Field | Default |
|---|---|
| Username | `admin` |
| Password | `Admin12345` |

> ⚠️ Change these in `.env` before deploying!

---

## ☁️ Deployment (Render Free Plan)

### Steps
1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — no manual config needed
5. Set the following environment variables in Render dashboard:

| Env Var | Value |
|---|---|
| `ADMIN_EMAIL` | your-admin@email.com |
| `ADMIN_PASSWORD` | YourStrongPassword |
| `SECRET_KEY` | (auto-generated by Render) |

6. Click **Deploy**
7. First deploy takes ~5-8 minutes (downloads SFace model)

### Free Plan Limitations
| Limitation | Detail |
|---|---|
| **Cold starts** | App sleeps after 15min inactivity; ~30-60s wake time |
| **No persistent disk** | SQLite DB resets on each redeploy |
| **Single worker** | 1 Gunicorn worker only |
| **CPU limit** | 0.1 CPU shared |

> 💡 To avoid data loss on redeploy: switch to PostgreSQL by setting `DATABASE_URL` env var (pg8000 driver already installed).

---

## 🔐 Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `SECRET_KEY` | dev-secret | ✅ Yes | Flask session encryption key |
| `FLASK_ENV` | development | ✅ Yes | `production` on Render |
| `DB_PATH` | `attendance_system.db` | No | SQLite file path |
| `ADMIN_USERNAME` | `admin` | No | Admin login username |
| `ADMIN_EMAIL` | `admin@gmail.com` | ✅ Yes | Admin email |
| `ADMIN_PASSWORD` | `Admin12345` | ✅ Yes | Admin password |
| `FACE_RECOGNITION_THRESHOLD` | `12.0` | No | SFace L2 distance threshold |
| `SCHEDULER_ENABLED` | `true` | No | Enable/disable APScheduler |
| `SESSION_TIMEOUT_MINUTES` | `30` | No | Session expiry |

---

## 🔒 Security Considerations

| Area | Implementation |
|---|---|
| **Password storage** | PBKDF2-HMAC-SHA256, 100,000 iterations, fixed salt |
| **Session security** | HttpOnly + Secure cookies in production |
| **CSRF** | Flask-WTF token on all forms |
| **SQL injection** | Parameterized queries via sqlite3 |
| **Face data** | Embeddings only (no images stored) |
| **Role enforcement** | `@login_required` + `@role_required('admin')` decorators |
| **Audit trail** | All actions logged to `audit_logs` table |

> ⚠️ **Note:** The current PBKDF2 salt is a fixed string. For production, use a random per-user salt. Consider upgrading to `bcrypt` or `argon2`.

---

## ⚠️ Known Limitations

| # | Limitation | Workaround |
|---|---|---|
| 1 | SQLite not persistent on free Render plan | Use PostgreSQL / paid plan |
| 2 | Single Gunicorn worker — no concurrent requests | Upgrade to paid plan |
| 3 | Cold start delay on free plan | Use a cron job to ping `/health` every 14 min |
| 4 | Face recognition slow on CPU (~2-3s) | GPU instance (paid) or use smaller image resolution |
| 5 | EmailJS keys hardcoded in camera.html | Move to env vars |
| 6 | Fixed PBKDF2 salt (not per-user) | Upgrade to bcrypt |
| 7 | No email verification on signup | Add SendGrid / SMTP flow |

---

## 🤝 Contributing

1. Fork the repo
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'feat: add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

### Commit Convention
| Prefix | Usage |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation |
| `refactor:` | Code refactoring |
| `chore:` | Maintenance |

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">

Made with ❤️ by [Suprabh Sharma](https://github.com/SuprabhSharma)

⭐ Star this repo if it helped you!

</div>
