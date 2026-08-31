<div align="center">

# FaceAttend

### AI-Powered Biometric Attendance for Modern Workplaces

[![Live](https://img.shields.io/badge/Live-faceattend--live.duckdns.org-0d7a6a?style=for-the-badge&logo=googlechrome&logoColor=white)](https://faceattend-live.duckdns.org)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![DeepFace](https://img.shields.io/badge/DeepFace-SFace-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)](https://github.com/serengil/deepface)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Project-lightgrey?style=for-the-badge)](#)

**Contactless face recognition · Real-time attendance · Secure Gmail OTP · Admin analytics · PWA**

[Open Live App](https://faceattend-live.duckdns.org) · [Employee Login](https://faceattend-live.duckdns.org/auth/login) · [Admin Login](https://faceattend-live.duckdns.org/auth/admin-login)

</div>

---

## Overview

**FaceAttend** is a production-oriented biometric attendance platform. Employees register a face once, then mark attendance with a webcam scan. Status is resolved consistently for employees and admins, with shift rules, Gmail OTP flows, and dual SQLite / PostgreSQL support.

Built for classrooms and offices that need **fast check-in**, **clear auditability**, and **self-service account recovery**—without SMS costs.

| Pillar | What you get |
|--------|----------------|
| **Identity** | SFace embeddings, one face per employee, re-register when needed |
| **Attendance** | Present / late / half-day / pending / absent with shared rules |
| **Access** | Flask-Login, role separation (employee vs admin) |
| **Recovery** | 4-digit Gmail OTP for employees only; admin is server-managed |
| **Ops** | Docker on EC2, Nginx + HTTPS, persistent volume for SQLite |

---

## Features

### Biometrics & check-in
- **One-time face enrollment** with optional **re-register** if recognition fails
- **SFace** (DeepFace) — compact model, Euclidean L2 matching
- **Configurable match threshold** (`FACE_RECOGNITION_THRESHOLD`, default **12.0** for SFace L2)
- Camera terminal for mark attendance; blocks check-in until enrolled
- Admin accounts are **exempt** from face attendance

### Attendance intelligence
- Shared status engine for **dashboard**, **reports**, and **admin live roster**
- **Pending** before shift close when there is no punch; **absent** after close or for past missed workdays
- Shift window oriented around **office hours** (e.g. 9:00–17:00 IST with late / half-day bands)
- Live working-hours counter, week strip, streak, and history with synthesized workdays
- Admin today board: present / late / half-day / absent / pending counts and filters

### Accounts & security
- Employee registration with **6-digit Gmail SMTP OTP** (account created only after verify)
- **Forgot password** for employees: **4-digit Gmail OTP** → set new password *or* keep current → **auto sign-in**
- **Administrators cannot** use self-service password recovery
- Default admin bootstrapped from environment on first start; password stored **hashed** in DB
- Session cookies, role guards, secure password hashing (PBKDF2)
- Anti-enumeration messaging on recovery (no email existence leak)

### Product experience
- Responsive UI: dashboard, camera, reports, profile, admin users
- PWA manifest + service worker for installable access
- Near real-time dashboard refresh of attendance state

### Platform
- **SQLite** (local / Docker volume) or **PostgreSQL** (`DATABASE_URL`) with fallback patterns
- Docker image + Gunicorn; Nginx reverse proxy in production
- Background scheduler hooks for attendance-related jobs

---

## Architecture

```text
Browser (PWA) ──HTTPS──► Nginx ──► Gunicorn / Flask
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              Auth + OTP         Face service      Attendance API
              (Gmail SMTP)         (SFace)         (status engine)
                    │                 │                 │
                    └─────────────────┴─────────────────┘
                                      ▼
                         SQLite volume  or  PostgreSQL
```

---

## Shift & status rules

| Condition | Status |
|-----------|--------|
| Check-in on time (within policy window) | `present` |
| Check-in after grace, before midday band | `late` |
| Check-in in afternoon band | `half_day` |
| No check-in, same day, before shift end | `pending` |
| No check-in after shift end, or past workday missed | `absent` |
| Out-of-window / invalid punch handling | treated as absent where configured |

Dashboard, employee reports, and admin views use the **same resolver** so numbers stay aligned.

---

## Core user flows

### Employee
1. Register with name + Gmail → verify **6-digit** email OTP
2. **Register face** once (re-register available if needed)
3. **Mark attendance** at the camera during open hours
4. Track today / week / history on dashboard and reports
5. Recover access via **Forgot password** → **4-digit** OTP → update or keep password → **signed in automatically**

### Administrator
1. Sign in on **Admin Login** only
2. Live roster for the day, filters, enrollment state
3. User management (employees; admin protected from casual delete)
4. Password is **not** recoverable via the public forgot-password flow

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Runtime | Python 3.10 |
| Web | Flask 3, Flask-Login, Jinja2 |
| AI | DeepFace · **SFace** embeddings |
| DB | SQLite and/or PostgreSQL |
| Mail | Gmail SMTP (STARTTLS) for OTP only |
| Process | Gunicorn |
| Deploy | Docker, Nginx, TLS (typical) |
| Edge | PWA (manifest + service worker) |

---

## Repository layout

```text
face-attendance-deepface/
├── app/
│   ├── __init__.py          # Application factory
│   ├── models/db.py         # Schema, attendance logic, OTP tables
│   ├── routes/              # auth, views, api
│   ├── services/            # face_service, email_service, scheduler
│   ├── templates/           # UI (auth, dashboard, admin, camera)
│   └── static/              # CSS, JS, PWA assets
├── run.py
├── requirements.txt
├── Dockerfile
├── .env.example             # Template only — never commit real secrets
└── README.md
```

---

## API surface (selected)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/register-user` | Enroll / force re-enroll face |
| `POST` | `/api/recognize-face` | Match face and mark attendance |
| `GET` | `/api/attendance` | Employee history (canonical statuses) |
| `GET` | `/api/admin/attendance/today` | Live roster for all active employees |
| `GET` | `/api/admin/attendance/history/<user_id>` | Per-user history for admins |

Auth pages (HTML): login, register, verify-email, forgot-password, verify-reset-otp, reset-password, profile, change-password.

---

## Quick start (local)

```bash
git clone https://github.com/SuprabhSharma/face-attendance-deepface.git
cd face-attendance-deepface

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your own secret key, admin bootstrap, optional SMTP, threshold

python run.py
```

Open the local URL shown by the app (typically port 5000 unless configured otherwise).

### Docker (production-style)

```bash
docker build -t face-attendance .

docker run -d \
  --name face-attendance-app \
  --restart unless-stopped \
  --env-file .env \
  -p 127.0.0.1:10000:10000 \
  -v /path/to/persistent-data:/app/data \
  face-attendance
```

Place Nginx in front with TLS. Use `--restart unless-stopped` so the container returns after host reboot.

---

## Configuration

Copy `.env.example` → `.env`. Configure using **your own** values (never commit real secrets).

| Area | Variable names |
|------|----------------|
| App | `FLASK_ENV`, `SECRET_KEY`, `DEBUG` |
| Database | `DB_PATH` and/or `DATABASE_URL` |
| Admin bootstrap | `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_FULL_NAME` |
| Face match | `FACE_RECOGNITION_THRESHOLD` (**12.0** for SFace L2; cosine-style values like `0.80` are auto-corrected) |
| SMTP OTP | `SMTP_ENABLED`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS` |
| OTP policy | `OTP_EXPIRES_MINUTES`, `OTP_MAX_ATTEMPTS`, `OTP_RESEND_COOLDOWN_SECONDS`, `OTP_MAX_RESENDS` |
| Session | `SESSION_TIMEOUT_MINUTES` |

**Never commit `.env`.** On servers: `chmod 600 .env`.

SMTP should use a **provider app password** workflow for the mail account—not a normal login password stored in the repo.

Email delivery depends on provider quotas and spam filters; failed sends do not create accounts or complete password resets.

---

## Security notes

- Passwords and OTPs are **hashed** at rest; OTPs are single-use with expiry and attempt limits
- Employee recovery only; **admin self-service recovery is disabled**
- Face threshold must match the model distance metric (SFace L2 ≈ 12.0)
- Run HTTPS in production; keep application secrets strong and private
- Biometrics are stored as embedding vectors in the default design (not a public photo gallery)

---

## Operational tips

| Symptom | Likely cause |
|---------|----------------|
| Nginx **502** after reboot | App container not running — start with `--restart unless-stopped` |
| Face enrolled but not recognized | Wrong threshold or stale embedding — use **12.0** and re-register face |
| Dashboard vs admin status mismatch | Use latest shared status resolver; hard-refresh the browser |
| OTP email missing | SMTP off/misconfigured, spam folder, or provider limits |

---

## Roadmap

- Stronger liveness / anti-spoof challenges
- Classroom presence signals (session codes, optional proximity hardware)
- Richer admin analytics and export
- Multi-tenant organization support

---

## Disclaimer

Recognition accuracy depends on lighting, camera quality, pose, and threshold tuning. Operators are responsible for privacy notices, workplace policy, and compliance. OTP email is best-effort and not a guaranteed delivery SLA.

---

## Credits

- [DeepFace](https://github.com/serengil/deepface) / SFace
- Flask and the Python web ecosystem

---

<div align="center">

**FaceAttend** — biometric attendance with clear status, secure OTP, and production ops in mind.

[Live demo](https://faceattend-live.duckdns.org) · [Repository](https://github.com/SuprabhSharma/face-attendance-deepface)

</div>
