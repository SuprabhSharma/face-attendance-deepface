<div align="center">

# ⚡ Face Attendance DeepFace

### Enterprise Biometric Attendance & Real-Time Workforce Analytics Platform

[![Live Demo](https://img.shields.io/badge/Live%20Demo-faceattend--live.duckdns.org-007ACC?style=for-the-badge&logo=googlechrome&logoColor=white)](https://faceattend-live.duckdns.org)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![DeepFace](https://img.shields.io/badge/Model-SFace%20(28MB)-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)](https://github.com/serengil/deepface)
[![PostgreSQL](https://img.shields.io/badge/Database-AWS%20RDS%20PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://aws.amazon.com/rds/)
[![Docker](https://img.shields.io/badge/Deployment-AWS%20EC2%20%2B%20Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![SSL](https://img.shields.io/badge/SSL-Let's%20Encrypt%20(HTTPS)-003A70?style=for-the-badge&logo=letsencrypt&logoColor=white)](https://letsencrypt.org/)

<br />

**A production-grade, AI-powered corporate biometric attendance tracking system engineered with lightweight Edge AI face embeddings (SFace), real-time check-in analytics, automated shift compliance, and dual SQLite/PostgreSQL persistence.**

<br />

[🚀 Open Live Application](https://faceattend-live.duckdns.org) • [💻 GitHub Repository](https://github.com/SuprabhSharma/face-attendance-deepface) • [🔑 Admin Portal](https://faceattend-live.duckdns.org/auth/admin-login)

</div>

---

## 📑 Table of Contents

- [Executive Summary](#-executive-summary)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Shift Rules & Corporate Logic Engine](#-shift-rules--corporate-logic-engine)
- [Core Workflows](#-core-workflows)
- [Technology Stack](#-technology-stack)
- [Repository Structure](#-repository-structure)
- [Database Schema & Data Models](#-database-schema--data-models)
- [API Reference](#-api-reference)
- [Local Installation & Setup](#-local-installation--setup)
- [Environment Configuration](#-environment-configuration)
- [Production Deployment (AWS EC2 + RDS)](#-production-deployment-aws-ec2--rds)
- [Security & Performance Engineering](#-security--performance-engineering)
- [Known Limitations & Roadmap](#-known-limitations--roadmap)
- [Author & License](#-author--license)

---

## 📌 Executive Summary

### The Problem
Traditional attendance management methods (RFID cards, biometric fingerprint hardware, and manual registers) suffer from **buddy punching**, hardware wear and tear, high maintenance overhead, and latency in synchronizing branch data with corporate reporting systems. Conversely, heavy deep learning models (like VGG-Face or ResNet50) demand expensive dedicated GPU clusters and introduce latency bottlenecks during multi-user morning rush check-ins.

### The Solution
**Face Attendance DeepFace** delivers zero-touch, client-side webcam streaming coupled with server-side **SFace (28MB)** facial embedding extraction. SFace is edge-optimized, requiring **no GPU** while achieving sub-second L2 distance vector matching. The architecture is wrapped in a high-concurrency Flask runtime running on **AWS EC2** with managed **AWS RDS PostgreSQL** storage, background cron schedulers for automated absentee marking, and PWA (Progressive Web App) offline caching capabilities.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Client_Layer ["Client Layer (Browser / Mobile PWA)"]
        UI["Jinja2 / HTML5 / Modern CSS"]
        CAM["Webcam.js / Canvas Stream (320x240)"]
        SW["Service Worker (sw.js) & PWA Manifest"]
    end

    subgraph Reverse_Proxy ["Edge Reverse Proxy"]
        NGINX["Nginx (Reverse Proxy & Rate Limiter)"]
        SSL["Let's Encrypt TLS (Certbot Auto-Renew)"]
    end

    subgraph Application_Layer ["Application Container (AWS EC2 / Docker)"]
        GUNICORN["Gunicorn WSGI (Workers)"]
        FLASK["Flask 3.0 Application Factory"]
        AUTH["Flask-Login & PBKDF2 Auth"]
        SCHEDULER["APScheduler (Cron Engine)"]
        FACE_ENGINE["DeepFace Engine (SFace Model - 28MB)"]
        OPENCV["OpenCV Headless (Detector Backend)"]
    end

    subgraph Persistence_Layer ["Data Layer (AWS RDS)"]
        PG[("AWS RDS PostgreSQL / Local SQLite3")]
        USERS[("users (Biometric Vectors)")]
        ATTENDANCE[("attendance (Timestamp & Status)")]
        AUDIT[("audit_logs & reports")]
    end

    CAM -->|Encrypted HTTPS Stream| NGINX
    NGINX -->|127.0.0.1:10000| GUNICORN
    GUNICORN --> FLASK
    FLASK --> AUTH
    FLASK --> FACE_ENGINE
    FACE_ENGINE --> OPENCV
    FLASK --> PG
    SCHEDULER -->|17:01 IST Auto-Absent Trigger| PG
    PG --- USERS
    PG --- ATTENDANCE
    PG --- AUDIT
```

---

## ✨ Key Features

### 👤 Biometric Face Recognition (SFace Model)
- **Ultra-Lightweight Weights:** Uses the 28MB SFace architecture preloaded into memory on application startup to eliminate cold-start inference latency.
- **Server-Side Downscaling:** High-resolution webcam frames are automatically normalized to `320x240` prior to embedding extraction, preserving server CPU while ensuring accurate landmark mapping.
- **Vector Euclidean Comparison:** 128-dimensional facial embedding vectors are stored in PostgreSQL and matched against live scans using configurable L2 distance thresholds (`DEFAULT_MATCH_THRESHOLD = 12.0`).
- **Duplicate Biometric Protection:** Prevents duplicate facial registrations across multiple user accounts via cross-database vector distance verification.

### 🏢 Corporate Shift Enforcement (IST Timezone)
- **Strict Check-In Windows:** Enforces corporate shifts (09:00 AM – 05:00 PM IST) with automatic grace period calculation:
  - `06:00 - 09:15`: **Present (On-Time)**
  - `09:16 - 13:00`: **Late Arrival**
  - `13:01 - 17:00`: **Half Day**
  - `After 17:00 / Sunday`: **Terminal Locked (Rejected)**
- **Automatic Absentee Marking:** Built-in `APScheduler` cron automatically sweeps database records daily at 17:01 IST, marking non-checked-in active employees as `absent`.

### 🛡️ Role-Based Access Control (RBAC) & Audit Trails
- **Isolated Entry Portals:** Segregated login controllers for Employees (`/auth/login`) and System Administrators (`/auth/admin-login`).
- **Administrative Immutability:** Strict safeguards prevent deletion or de-escalation of root administrator accounts.
- **Audit Logging:** Every user enrollment, profile modification, attendance purge, and deletion is recorded in `audit_logs` with timestamps and client IP addresses.

### 📊 Real-Time Operations Dashboard & Export Center
- **Live On-Duty Counter:** Dynamic polling endpoint (`/api/live-working-count`) calculating active employees on shift in real time.
- **Biometric Enrollment Coverage:** Live metrics on company-wide biometric registration rates and check-in percentages.
- **Multi-Format Reports:** Export attendance logs in CSV, Excel (`.xlsx`), or PDF formats with custom date range filters.

### 📱 Progressive Web App (PWA)
- Integrated service worker (`/sw.js`) and web app manifest (`/manifest.json`) enabling home screen installation on iOS and Android devices with full HTTPS camera permissions.

---

## ⏰ Shift Rules & Corporate Logic Engine

```
 06:00 AM            09:00 AM      09:15 AM                 01:00 PM                 05:00 PM     17:01 PM
    ├───────────────────┼─────────────┼────────────────────────┼────────────────────────┼───────────┤
    │◄─── Early Open ──►│◄── Grace ──►│◄──── Late Arrival ────►│◄───── Half Day ───────►│  LOCKED   │ (Cron Run)
    │     (Present)     │  (Present)  │      (Late Mark)       │     (Half-Day Mark)    │ (Absent)  │ Auto-Absent
```

| Time Window (IST) | Computed Status | Shift Treatment | System Action |
|:---|:---|:---|:---|
| **Before 06:00 AM** | `Rejected` | Out of Office Hours | Scan rejected (`office_closed_early`) |
| **06:00 AM – 09:15 AM** | `present` | Full Day (On-Time with 15m Grace) | Recorded & Timed In |
| **09:16 AM – 01:00 PM** | `late` | Full Day (Late Arrival) | Recorded with late flag |
| **01:01 PM – 05:00 PM** | `half_day` | Half Day Credit | Recorded with half-day flag |
| **After 05:00 PM** | `Rejected` | Shift Closed | Scan rejected; flagged as absent |
| **Sunday (Day 6)** | `Rejected` | Weekly Off | Scan rejected (`office_closed_sunday`) |
| **Daily at 17:01:00** | `absent` | Non-Attendant Sweeper | Auto-inserted by APScheduler |

---

## 🔄 Core Workflows

### 1. Employee Biometric Enrollment Flow
```mermaid
sequenceDiagram
    autonumber
    actor Employee
    participant Browser as Client Browser (Webcam)
    participant API as /api/register-face
    participant Model as SFace Model (DeepFace)
    participant DB as AWS RDS PostgreSQL

    Employee->>Browser: Opens /register & captures photo
    Browser->>API: POST Base64 image payload
    API->>Model: Normalize frame (320x240) & extract 128-d vector
    Model-->>API: Facial embedding vector
    API->>DB: Scan existing embeddings for duplicate distance (< 12.0)
    alt Duplicate Face Found
        API-->>Browser: HTTP 400 "Biometric already registered to another user"
    else Unique Embedding
        API->>DB: UPDATE users SET embedding = [...] WHERE id = user_id
        API-->>Browser: HTTP 200 "Face registered successfully"
    end
```

### 2. Live Facial Attendance Scanning Flow
```mermaid
sequenceDiagram
    autonumber
    actor Employee
    participant Camera as Attendance Terminal (/camera)
    participant API as /api/mark-attendance
    participant Engine as Biometric Engine
    participant DB as AWS RDS PostgreSQL

    Employee->>Camera: Stands in front of terminal camera
    Camera->>API: POST Base64 frame snapshot
    API->>Engine: Extract vector & compute L2 distance against active users
    Engine-->>API: Match: user_id (Distance: 6.42, Threshold: 12.0)
    API->>DB: Check if attendance already marked today
    alt Already Marked
        API-->>Camera: HTTP 400 "Attendance already recorded for today"
    else First Scan of Day
        API->>API: Evaluate IST shift rules (Time-In: 09:08 AM -> "present")
        API->>DB: INSERT INTO attendance (user_id, date, time_in, status)
        API-->>Camera: HTTP 200 "Welcome, John Doe (Status: Present)"
    end
```

---

## 🛠️ Technology Stack

| Layer | Technology | Version | Purpose |
|:---|:---|:---|:---|
| **Language** | Python | `3.10.13` | Backend execution runtime |
| **Web Framework** | Flask | `3.0.0` | Modular WSGI application framework |
| **WSGI Server** | Gunicorn | `21.2.0` | Production HTTP process manager |
| **Deep Learning Engine** | DeepFace | `0.0.83` | Biometric representation & verification pipeline |
| **Facial Model** | SFace | `28 MB` | Lightweight edge facial recognition model |
| **Computer Vision** | OpenCV Headless | `4.8.1.78` | Frame decoding, spatial resizing & detector backend |
| **ML Backend** | TensorFlow / Keras | `2.12.0` | Tensor manipulation & embedding math |
| **Numerical Engine** | NumPy | `1.23.5` | Fast Euclidean (L2) distance vector calculations |
| **Primary Database** | AWS RDS PostgreSQL | `15.x` | Managed cloud relational storage & vector persistence |
| **Fallback Database** | SQLite3 | Native | Zero-dependency local persistence layer |
| **DB Driver** | psycopg2-binary | `2.9.9` | High-performance PostgreSQL interface |
| **Task Scheduler** | APScheduler | `3.10.4` | Background cron scheduler for shift compliance |
| **Session Security** | Flask-Login | `0.6.3` | Cookie session management & RBAC decorators |
| **Web Server / SSL** | Nginx + Certbot | `1.28` | Reverse proxy, static asset delivery & TLS termination |
| **Containerization** | Docker | Linux x86_64 | Containerized multi-stage application image |

---

## 📂 Repository Structure

```
face-attendance-deepface/
├── app/
│   ├── __init__.py               # Flask application factory, scheduler & model preloader
│   ├── models/
│   │   └── db.py                 # Unified PostgreSQL/SQLite wrapper, DDL schema, CRUD & RBAC
│   ├── routes/
│   │   ├── api.py                # REST endpoints: face match, biometric registration, reports, stats
│   │   ├── auth.py               # Authentication controller: login, admin-login, register, passwords
│   │   └── views.py              # Page view handlers, PWA routes (sw.js, manifest.json)
│   ├── services/
│   │   ├── email_service.py      # Automated notification dispatcher (attendance & daily reports)
│   │   ├── face_service.py       # SFace vector extraction, normalization & L2 distance matcher
│   │   └── scheduler.py          # APScheduler cron configuration for shift compliance & reports
│   ├── static/                   # CSS stylesheets, frontend JavaScript, icons & PWA assets
│   ├── templates/                # Jinja2 HTML templates (Admin console, employee views, auth)
│   └── utils/
│       ├── helpers.py            # Date/time utilities, IST formatters, CSV/Excel/PDF exporters
│       └── logging_config.py     # Production logger configuration
├── clear_all_users.py            # Maintenance utility: Purges all users and biometric embeddings
├── clear_attendance.py           # Maintenance utility: Resets attendance records
├── Dockerfile                    # Container definition (Python 3.10-slim + OpenCV + SFace bake)
├── Procfile                      # Process declaration file for PaaS environments
├── render.yaml                   # Infrastructure-as-code declaration for Render deployments
├── requirements.txt              # Pinned Python package dependencies
├── run.py                        # Application entry point
└── runtime.txt                   # Explicit runtime version (Python 3.10.13)
```

---

## 🗄️ Database Schema & Data Models

The data layer uses an adaptive interface (`DBConnectionWrapper` in [`app/models/db.py`](app/models/db.py)) that automatically initializes identical DDL structures across **PostgreSQL** or **SQLite3**.

```mermaid
erDiagram
    users ||--o{ attendance : "has"
    users ||--o{ attendance_reports : "aggregates"
    users ||--o{ email_notifications : "receives"
    users ||--o{ audit_logs : "triggers"

    users {
        int id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        varchar full_name
        text embedding "JSON 128-d Vector"
        text profile_picture
        varchar role "admin | user | manager"
        varchar status "active | inactive"
        int is_verified
        timestamp created_at
        timestamp updated_at
    }

    attendance {
        int id PK
        int user_id FK
        date date
        time time_in
        time time_out
        varchar status "present | late | half_day | absent"
        text notes
        varchar marked_by "face_recognition | admin"
        timestamp created_at
        timestamp updated_at
    }

    working_hours {
        int id PK
        int day_of_week UK "0=Mon to 6=Sun"
        time start_time
        time end_time
        int is_working_day
    }

    attendance_reports {
        int id PK
        int user_id FK
        text report_type "daily | weekly | monthly"
        text report_date
        int total_present
        int total_absent
        int total_late
        int total_half_day
        text report_data
        timestamp created_at
    }

    email_notifications {
        int id PK
        int user_id FK
        text email_type
        text recipient_email
        text subject
        text status "pending | sent | failed"
        timestamp sent_at
        timestamp created_at
    }

    audit_logs {
        int id PK
        int user_id
        text action
        text resource_type
        int resource_id
        text details
        text ip_address
        timestamp timestamp
    }
```

---

## 🔌 API Reference

### Biometric & Attendance APIs

| Method | Endpoint | Description | Auth Required | Payload / Query |
|:---|:---|:---|:---:|:---|
| `POST` | `/api/mark-attendance` | Matches webcam frame vector and records attendance | No | `{ "image": "data:image/jpeg;base64,..." }` |
| `POST` | `/api/register-face` | Enrolls biometric facial embedding for logged-in user | Yes | `{ "image": "data:image/jpeg;base64,..." }` |
| `POST` | `/api/test-face` | Evaluates face alignment and detection quality | No | `{ "image": "data:image/jpeg;base64,..." }` |

### Analytics & System Metrics

| Method | Endpoint | Description | Auth Required | Payload / Query |
|:---|:---|:---|:---:|:---|
| `GET` | `/api/live-working-count` | Real-time shift status & on-duty active headcount | No | `None` |
| `GET` | `/api/stats` | Company-wide attendance aggregations & enrollment stats | Yes (`admin`) | `None` |
| `GET` | `/api/check-ins` | Today's chronological stream of recorded check-ins | Yes | `None` |

### Administration & Audit

| Method | Endpoint | Description | Auth Required | Payload / Query |
|:---|:---|:---|:---:|:---|
| `GET` | `/api/admin/detailed-report` | Detailed matrix of user attendance records with filters | Yes (`admin`) | `?date=YYYY-MM-DD` |
| `GET` | `/api/admin/audit-logs` | Chronological audit log trail of security & user actions | Yes (`admin`) | `?limit=50` |
| `GET` | `/api/export-attendance` | Export logs to downloadable CSV, Excel, or PDF | Yes | `?format=csv&start_date=...` |
| `GET` | `/health` | Application & container health probe | No | `None` (Returns `200 OK`) |

---

## 💻 Local Installation & Setup

### Prerequisites
- **Python:** `3.10.x` (Recommended for full TensorFlow 2.12 compatibility)
- **C++ Build Tools / CMake:** Required for compiling image dependencies
- **Git**

### 1. Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/SuprabhSharma/face-attendance-deepface.git
cd face-attendance-deepface

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 3. Initialize Environment Variables
Copy the example environment configuration file:
```bash
cp .env.example .env
```

### 4. Run Development Server
```bash
python run.py
```
Access the application at `http://127.0.0.1:5000`.

---

## ⚙️ Environment Configuration

| Variable | Type | Default | Purpose |
|:---|:---|:---|:---|
| `FLASK_ENV` | String | `production` | Runtime mode (`development` / `production`) |
| `SECRET_KEY` | String | `dev-secret-...` | Session cookie cryptographic signing secret |
| `DATABASE_URL` | String | *Empty (SQLite)* | PostgreSQL connection URI (`postgresql://user:pass@host:5432/dbname`) |
| `DB_PATH` | String | `attendance_system.db` | Fallback SQLite database file path |
| `ADMIN_USERNAME` | String | `admin` | Default root administrator username |
| `ADMIN_EMAIL` | String | `admin@example.com` | Default root administrator email |
| `ADMIN_PASSWORD` | String | `XXXXXXXXXX` | Default root administrator password |
| `FACE_RECOGNITION_THRESHOLD` | Float | `12.0` | SFace Euclidean L2 distance cutoff (Lower = Stricter) |
| `SCHEDULER_ENABLED` | Boolean | `True` | Activates background APScheduler cron workers |
| `TIMEZONE` | String | `Asia/Kolkata` | Operational timezone for shift boundaries |
| `SESSION_TIMEOUT_MINUTES` | Integer | `30` | Inactivity session cookie lifetime |
| `PORT` | Integer | `10000` | Port bound by Gunicorn in container environments |
| `SMTP_ENABLED` | Boolean | `false` | Enable Gmail SMTP for registration OTP emails |
| `SMTP_HOST` | String | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | Integer | `587` | SMTP port (587 + STARTTLS recommended) |
| `SMTP_USERNAME` | String | — | Authenticated Gmail address |
| `SMTP_PASSWORD` | String | — | **Gmail App Password** (not the account password) |
| `SMTP_FROM` | String | — | From address (same Gmail or authorized alias) |
| `SMTP_USE_TLS` | Boolean | `true` | Use STARTTLS |
| `SMTP_TIMEOUT_SECONDS` | Integer | `10` | SMTP socket timeout |
| `OTP_EXPIRES_MINUTES` | Integer | `10` | OTP lifetime |
| `OTP_MAX_ATTEMPTS` | Integer | `5` | Max wrong-code attempts per pending registration |
| `OTP_RESEND_COOLDOWN_SECONDS` | Integer | `60` | Minimum seconds between resends |
| `OTP_MAX_RESENDS` | Integer | `3` | Max resends per pending registration |

---



## 🔑 Password recovery (4-digit Gmail OTP)

Industry-style recovery without SMS (SMS is paid; Gmail on the user’s phone is free and near real-time):

1. **Forgot password** → enter registered `@gmail.com` address.
2. If an account exists, a **4-digit OTP** is emailed (hashed at rest, single-use, expiry + attempt + resend limits — same controls as registration OTP).
3. User enters the code → identity verified.
4. User can **set a new password** or **continue without changing** (return to sign-in with the old password).
5. Responses never confirm whether the email is registered (anti-enumeration).

Requires the same `SMTP_*` settings as registration OTP. Delivery is not guaranteed (spam filters, Gmail limits).

## 📧 Gmail SMTP OTP Registration

New user accounts are created only after a one-time email verification code is confirmed.

### Flow
1. User submits name, Gmail, and password at `/auth/register`.
2. The server validates fields and checks for duplicate name/email.
3. A cryptographically secure **6-digit OTP** is generated, **hashed**, and stored in `pending_email_verifications` (never plaintext OTP or password).
4. The OTP is emailed via **Gmail SMTP**.
5. User enters the code at `/auth/verify-email`.
6. On success the account is created with `is_verified=1` and the pending row is marked used (single-use).
7. Failed SMTP sends do **not** create an account.

OTP is **not** required for login, face biometric registration (`/api/register-user`), or attendance scanning.

### Gmail App Password setup
1. Open [Google Account → Security](https://myaccount.google.com/security).
2. Enable **2-Step Verification**.
3. Create an **App password** (select Mail / Other).
4. Copy the 16-character password into `SMTP_PASSWORD` in `.env`.
5. Set `SMTP_USERNAME` and `SMTP_FROM` to that Gmail address.
6. Set `SMTP_ENABLED=true`.

### Important limitations
- Gmail requires 2-Step Verification and an App Password; normal account passwords will not work.
- Sender must be the authenticated Gmail account or an authorized alias.
- Gmail applies quotas, spam filtering, and throttling — **delivery is not guaranteed**.
- Only `@gmail.com` recipients are accepted (existing app policy).
- SMTP credentials must remain server-side and must never be committed to Git.
- If SMTP is disabled or sending fails, registration stops with a safe retry message; no user row is inserted.

---

## 🚀 Production Deployment (AWS EC2 + RDS)

The production deployment runs on an **AWS EC2 `t3.small`** host backed by a dedicated **AWS RDS PostgreSQL** instance, proxied by **Nginx** with **Let's Encrypt SSL**.

```
                           Internet Traffic
                                  │ (HTTPS: 443)
                                  ▼
                     ┌──────────────────────────┐
                     │   Nginx Reverse Proxy    │ (Let's Encrypt TLS)
                     └────────────┬─────────────┘
                                  │ (HTTP: 10000)
                                  ▼
                     ┌──────────────────────────┐
                     │    Docker Container      │
                     │  Gunicorn (WSGI Server)  │
                     │   Flask Web Application  │
                     │   SFace Biometric Model  │
                     └────────────┬─────────────┘
                                  │ (TCP: 5432)
                                  ▼
                     ┌──────────────────────────┐
                     │    AWS RDS PostgreSQL    │ (Multi-AZ / Auto Backups)
                     └──────────────────────────┘
```

### 1. Build and Run Container on AWS EC2
```bash
# Build optimized Docker image with pre-baked SFace weights
docker build -t face-attendance .

# Launch container mapped to internal port 10000
docker run -d \
  --name face-attendance-app \
  -p 127.0.0.1:10000:10000 \
  --env-file .env \
  --restart always \
  face-attendance
```

### 2. Nginx Reverse Proxy Configuration (`/etc/nginx/conf.d/face-attendance.conf`)
```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name faceattend-live.duckdns.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name faceattend-live.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/faceattend-live.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/faceattend-live.duckdns.org/privkey.pem;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:10000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🔒 Security & Performance Engineering

- **Cryptographic Password Hashing:** Uses `PBKDF2-HMAC-SHA256` with 100,000 iterations and dedicated salt bytes.
- **Biometric Vector Protection:** Raw biometric images are processed in-memory and discarded immediately after 128-dimensional embedding generation; raw image files are never permanently written to disk.
- **SQL Injection Prevention:** Unified query translation layer strictly parameterizes all input bindings across SQLite (`?`) and PostgreSQL (`%s`).
- **Memory & Latency Optimization:** SFace model weights (28MB) are preloaded in a background daemon thread upon Flask startup, guaranteeing sub-second response times on first user interaction.
- **Upload Size Protection:** Reverse proxy and WSGI layer enforce strict `MAX_UPLOAD_SIZE = 25MB` limits to guard against buffer overflow and denial-of-service attempts.

---

## ⚠️ Known Limitations & Roadmap

### Known Limitations
- **Lighting & Glare Sensitivity:** Extreme backlight conditions may impede initial OpenCV Haar-cascade facial bounding box detection.
- **Multi-Face Scene Handling:** When multiple faces appear simultaneously, the system selects the candidate with the largest bounding box area.

### Planned Roadmap
- [ ] Multi-tenant organization support with customizable shift schedules per department
- [ ] Liveness detection (blink & head turn verification) to eliminate photo spoofing
- [ ] Automated Slack / Microsoft Teams check-in notification webhooks
- [ ] Native iOS and Android shell wrappers using Capacitor

---

## 👤 Author & Maintainer

**Suprabh Sharma**
- GitHub: [@SuprabhSharma](https://github.com/SuprabhSharma)
- Repository: [SuprabhSharma/face-attendance-deepface](https://github.com/SuprabhSharma/face-attendance-deepface)
- Production System: [https://faceattend-live.duckdns.org](https://faceattend-live.duckdns.org)

---

## 📄 License

This project is licensed under the terms specified in the repository. See [LICENSE](LICENSE) for details.
