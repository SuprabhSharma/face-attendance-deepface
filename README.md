# 🎯 FaceAttend &mdash; Neural Face Recognition Attendance System

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Render%20Cloud-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SFace Biometrics](https://img.shields.io/badge/SFace_AI-28MB_Lightweight-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)](https://github.com/serengil/deepface)
[![SQLite](https://img.shields.io/badge/SQLite-Offline_Fallback-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)

**An enterprise-grade, browser-based biometric attendance ecosystem powered by lightweight neural face recognition and cloud PostgreSQL persistence.**

[🚀 Live Demo](https://face-attendance-deepface.onrender.com) &bull; [📖 Architecture](#-system-architecture) &bull; [🗄️ Database](#-cloud-postgresql--dual-engine-database) &bull; [📡 API Docs](#-api-reference) &bull; [⚡ Quickstart](#-getting-started-local)

</div>

---

## 📋 Table of Contents

1. [🌟 Key Highlights & Innovations](#-key-highlights--innovations)
2. [🏗️ System Architecture](#️-system-architecture)
3. [🤖 Neural Face Recognition Engine](#-neural-face-recognition-engine)
4. [🗄️ Cloud PostgreSQL & Dual-Engine Database](#️-cloud-postgresql--dual-engine-database)
5. [⏰ Background Automation & Scheduler](#-background-automation--scheduler)
6. [🔐 Authentication & Role Management](#-authentication--role-management)
7. [📊 Personal Attendance & Analytics](#-personal-attendance--analytics)
8. [📡 REST API Reference](#-rest-api-reference)
9. [📁 Project Directory Tree](#-project-directory-tree)
10. [⚡ Getting Started (Local Development)](#-getting-started-local-development)
11. [☁️ Production Deployment (Render)](#️-production-deployment-render)
12. [⚙️ Environment Variables Reference](#️-environment-variables-reference)
13. [🛡️ Security & Privacy Architecture](#️-security--privacy-architecture)
14. [📄 License](#-license)

---

## 🌟 Key Highlights & Innovations

* **Lightweight Neural Biometrics (SFace):** Only **28MB** memory footprint (compared to VGG-Face at 580MB), optimized specifically for CPU inference on cloud tiers (Render 512MB RAM free plan).
* **Dual-Engine Smart Database Adapter:** Automatically uses **Render Cloud PostgreSQL** in production when `DATABASE_URL` is set, and falls back to **local SQLite** for offline development.
* **Non-Blocking Background Warmup:** Preloads the face inference model in a daemon thread on server boot, ensuring sub-second response times without Gunicorn worker timeouts.
* **Automated Cron Jobs (`APScheduler`):**
  * Auto-marks absentees at 5:30 PM IST on working days (Mon–Fri).
  * Auto-generates daily summary logs at 6:00 PM IST.
  * Auto-compiles monthly attendance metrics at the end of each month.
* **Single Identity User Flow:** Unifies full name and login identity. Password visibility toggles (`👁`), live password strength evaluation, and duplicate registration protection.
* **Strict Anti-Duplicate Tracking:** Mathematical 24-hour timestamp verification prevents users from double-marking attendance on the same day.
* **Google-Grade UI/UX:** Responsive CSS Grid and Flexbox layout without screen overflow, responsive across 4K displays down to 375px mobile screens.

---

## 🏗️ System Architecture

```mermaid
graph TD
    Client["📱 Client Browser (Webcam / Canvas)"] -->|Base64 Frame Stream| Gunicorn["🌐 Gunicorn WSGI Server"]
    Gunicorn --> FlaskApp["⚙️ Flask Application Engine"]
    
    subgraph "Core Services"
        FlaskApp --> AuthModule["🔐 Flask-Login & PBKDF2 Auth"]
        FlaskApp --> FaceService["🤖 Face Service (SFace Engine)"]
        FlaskApp --> APScheduler["⏰ APScheduler Background Daemon"]
    end

    subgraph "Database Layer (Smart Adapter)"
        FlaskApp --> DBAdapter["🗄️ Unified DB Adapter (db.py)"]
        DBAdapter -->|DATABASE_URL present| PostgresDB[("🐘 Render PostgreSQL Cloud")]
        DBAdapter -->|Offline / Fallback| SQLiteDB[("💾 Local SQLite (attendance.db)")]
    end

    subgraph "Automation Triggers"
        APScheduler -->|17:30 IST| AutoAbsent["❌ Auto-Mark Absentees"]
        APScheduler -->|18:00 IST| DailySummary["📧 Daily Summaries"]
        APScheduler -->|Month End| MonthlyReport["📊 Monthly Metrics"]
    end
```

---

## 🤖 Neural Face Recognition Engine

The system uses **SFace** (Spherical Feature Face Recognition), an ultra-efficient deep convolutional network optimized for constrained hardware.

```
[ Webcam Capture ] ──> [ OpenCV Haar Cascade ] ──> [ Face Crop & Normalize ] ──> [ SFace ConvNet ] ──> [ 128-D Vector ]
                                                                                                               │
                                                                                                               ▼
[ Verified Attendance ] <── [ L2 Euclidean Distance < 12.0 ] <── [ Compare with Stored Embeddings ] <──────────┘
```

### Recognition Specifications:
* **Embedding Dimensionality:** 128 float values per face.
* **Storage Format:** JSON array stored in database `embedding` column.
* **Default Threshold:** `12.0` L2 Distance (Configurable via `FACE_RECOGNITION_THRESHOLD`).
* **Performance:** ~200ms – 400ms inference time on standard 1-vCPU cloud instances.

---

## 🗄️ Cloud PostgreSQL & Dual-Engine Database

The database layer in [`app/models/db.py`](app/models/db.py) provides a single, unified interface for both PostgreSQL and SQLite.

### Relational Schema (6 Core Tables):

```mermaid
erDiagram
    USERS ||--o{ ATTENDANCE : logs
    USERS ||--o{ ATTENDANCE_REPORTS : compiles
    USERS ||--o{ EMAIL_NOTIFICATIONS : receives
    USERS ||--o{ AUDIT_LOGS : records

    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        string full_name
        text embedding
        string role
        string status
        timestamp created_at
    }

    ATTENDANCE {
        int id PK
        int user_id FK
        string date
        string time_in
        string time_out
        string status
        string marked_by
        timestamp created_at
    }

    WORKING_HOURS {
        int id PK
        int day_of_week UK
        string start_time
        string end_time
        int is_working_day
    }

    ATTENDANCE_REPORTS {
        int id PK
        int user_id FK
        string report_type
        string report_date
        int total_present
        int total_absent
        int total_late
        text report_data
    }

    EMAIL_NOTIFICATIONS {
        int id PK
        int user_id FK
        string email_type
        string recipient_email
        string status
        timestamp sent_at
    }

    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string resource_type
        string ip_address
        timestamp timestamp
    }
```

---

## ⏰ Background Automation & Scheduler

The application runs an embedded non-blocking background scheduler (`APScheduler`) configured to Indian Standard Time (IST, UTC+5:30).

| Job ID | Frequency | Trigger Time | Action Description |
|---|---|---|---|
| `mark_absentees` | Mon &ndash; Fri | `17:30 IST` | Queries all active users without an attendance log for today and records status as `absent`. |
| `send_summaries` | Daily | `18:00 IST` | Compiles check-in logs and logs summary delivery status. |
| `monthly_reports` | Monthly (1st) | `23:00 IST` | Aggregates 30-day attendance rates and writes to `attendance_reports`. |

---

## 🔐 Authentication & Role Management

| Role | Permissions & Access Scope |
|---|---|
| **User** | Mark biometric attendance, access personal attendance history, view monthly attendance rate and streaks, update password. |
| **Admin** | Full system control: view all registered users, total system attendance logs, export Excel/CSV reports, deactivate users, adjust working hours. |

---

## 📊 Personal Attendance & Analytics

Users have access to an industry-grade personal report dashboard ([`app/templates/report.html`](app/templates/report.html)):
* **Real-time Stat Cards:** Present days this month, absent days, current consecutive streak, and attendance percentage.
* **Granular Filter Bar:** Filter history by specific month (`YYYY-MM`), status (`present`, `absent`, `late`), or exact date.
* **Auto Work Hours Calculation:** Dynamically calculates total shift duration when check-in and check-out timestamps are present.

---

## 📡 REST API Reference

### Face Registration & Matching
```http
POST /api/register
Content-Type: application/json

{
  "user_id": 1,
  "image": "data:image/jpeg;base64,..."
}
```
**Response (200 OK):**
```json
{
  "success": true,
  "message": "Face registered successfully",
  "data": { "user_id": 1, "status": "active" }
}
```

```http
POST /api/recognize
Content-Type: application/json

{
  "image": "data:image/jpeg;base64,..."
}
```
**Response (200 OK):**
```json
{
  "success": true,
  "match": true,
  "user": { "id": 1, "name": "Suprabh Sharma" },
  "distance": 4.32,
  "threshold": 12.0
}
```

### Attendance Operations
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/attendance` | Get attendance records for current user | Yes (Session) |
| `POST` | `/api/attendance/mark` | Manually mark attendance (Admin only) | Yes (Admin) |
| `GET` | `/api/users` | List all registered active users | Yes (Admin) |
| `GET` | `/health` | Cloud provider liveness probe | No |

---

## 📁 Project Directory Tree

```text
face-attendance-deepface/
├── app/
│   ├── __init__.py               # Flask application factory & background workers
│   ├── models/
│   │   ├── __init__.py
│   │   └── db.py                 # Smart Dual-Engine Adapter (PostgreSQL / SQLite)
│   ├── routes/
│   │   ├── api.py                # Biometric API endpoints & lazy model cache
│   │   ├── auth.py               # Authentication, registration & session handlers
│   │   └── views.py              # Front-end UI page controllers
│   ├── services/
│   │   ├── email_service.py      # Notification dispatcher
│   │   ├── face_service.py       # SFace embedding extractor & matcher
│   │   └── scheduler.py          # APScheduler background cron jobs
│   ├── static/
│   │   ├── css/style.css         # Core CSS design system
│   │   └── js/main.js            # Toast notifications & UI helpers
│   ├── templates/
│   │   ├── admin/                # Admin dashboards & user roster views
│   │   ├── auth/                 # 3-in-1 Authentication Portal
│   │   ├── base.html             # Main dashboard app shell
│   │   ├── camera.html           # Live camera attendance scanner
│   │   ├── index.html            # User dashboard
│   │   ├── register.html         # In-app webcam face enrollment
│   │   ├── report.html           # Personal attendance analytics
│   │   ├── navbar.html           # Top navigation bar
│   │   └── sidebar.html          # Collapsible responsive sidebar
│   └── utils/
│       └── logging_config.py     # Rotating file & console logger
├── attendance_system.db          # Local development SQLite file (auto-generated)
├── render.yaml                   # Render Infrastructure-as-Code blueprint
├── requirements.txt              # Production Python dependencies
├── run.py                        # WSGI entry point
└── README.md                     # Documentation
```

---

## ⚡ Getting Started (Local Development)

### 1. Clone the Repository
```bash
git clone https://github.com/SuprabhSharma/face-attendance-deepface.git
cd face-attendance-deepface
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Local `.env` Configuration
Create a `.env` file in the root directory:
```env
FLASK_ENV=development
SECRET_KEY=local-dev-secret-key-change-in-prod
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@gmail.com
ADMIN_PASSWORD=Admin12345
FACE_RECOGNITION_THRESHOLD=12.0
SCHEDULER_ENABLED=true
```

### 5. Launch the Application
```bash
python run.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## ☁️ Production Deployment (Render)

### 1. Deploy via `render.yaml` Blueprint
1. Fork or push this repository to your GitHub account.
2. In the **[Render Dashboard](https://dashboard.render.com)**, click **New +** ➔ **Blueprint**.
3. Select this repository. Render will automatically parse `render.yaml` and configure the web service.

### 2. Connect Free Render PostgreSQL (Permanent Storage)
1. In Render, click **New +** ➔ **PostgreSQL**.
2. Set Name to `attendance-db`, choose Plan **Free**, and click **Create Database**.
3. Copy the **Internal Database URL**.
4. In your Web Service settings ➔ **Environment**, add:
   * **Key:** `DATABASE_URL`
   * **Value:** `postgres://user:password@dpg-xxxxxx-a:5432/attendance_db`
5. Click **Save Changes**. The server will automatically migrate tables to PostgreSQL on startup.

---

## ⚙️ Environment Variables Reference

| Variable Name | Default Value | Description |
|---|---|---|
| `FLASK_ENV` | `production` | Environment mode (`development` or `production`). |
| `SECRET_KEY` | *(Required)* | Secret key for signing session cookies. |
| `DATABASE_URL` | *(None)* | PostgreSQL connection URI. If omitted, SQLite is used. |
| `ADMIN_USERNAME` | `admin` | Default administrator username created on boot. |
| `ADMIN_PASSWORD` | `Admin12345` | Default administrator password. |
| `ADMIN_EMAIL` | `admin@gmail.com` | Administrator email address. |
| `FACE_RECOGNITION_THRESHOLD` | `12.0` | SFace L2 distance threshold (lower = stricter). |
| `SCHEDULER_ENABLED` | `true` | Enables or disables background cron jobs. |
| `SESSION_TIMEOUT_MINUTES` | `30` | Inactivity session timeout in minutes. |

---

## 🛡️ Security & Privacy Architecture

* **PBKDF2-HMAC-SHA256:** Passwords are never stored in plaintext. They are salted and hashed with 100,000 PBKDF2 iterations.
* **Mathematical Vector Irreversibility:** Stored face embeddings are one-way 128-dimensional mathematical coordinates. Original raw face photos are discarded immediately after embedding generation.
* **Rate Limiting & Timestamp Locks:** 24-hour verification lock prevents multiple attendance check-ins within a single calendar day.
* **Secure Cookie Flags:** In production, session cookies enforce `HttpOnly`, `SameSite=Lax`, and `Secure` SSL transmission.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

<div align="center">

Built with ❤️ by **[Suprabh Sharma](https://github.com/SuprabhSharma)**

</div>
