<div align="center">

# 🧠 FaceAttend

### Enterprise-Grade AI Face Recognition Attendance System

![Python](https://img.shields.io/badge/Python-3.10.13-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0.0-black?style=for-the-badge&logo=flask)
![DeepFace](https://img.shields.io/badge/DeepFace-SFace-orange?style=for-the-badge&logo=tensorflow)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker)
![Nginx](https://img.shields.io/badge/Nginx-reverse%20proxy-009639?style=for-the-badge&logo=nginx)
![AWS](https://img.shields.io/badge/AWS-EC2%20%2B%20RDS-FF9900?style=for-the-badge&logo=amazonaws)
![PWA](https://img.shields.io/badge/PWA-installable-5A0FC8?style=for-the-badge)

**Biometric attendance without hardware. Open a browser, look at your camera, done.**

Built on DeepFace SFace · Dual-DB (PostgreSQL / SQLite) · PWA-installable · Nginx HTTPS · Automated scheduling · Full audit trail

[![Live Application](https://img.shields.io/badge/Live%20Application-faceattend--live.duckdns.org-0d7a6a?style=for-the-badge&logo=googlechrome&logoColor=white)](https://faceattend-live.duckdns.org/)

</div>

---

## 📖 Table of Contents

1. [What is FaceAttend?](#-what-is-faceattend)
2. [Live System Architecture](#-live-system-architecture)
3. [Technology Stack](#-technology-stack)
4. [Core Feature Set](#-core-feature-set)
5. [AI Engine: How Face Recognition Works](#-ai-engine-how-face-recognition-works)
6. [Liveness Detection & Anti-Spoofing Architecture](#-liveness-detection--anti-spoofing-architecture)
7. [Database Architecture](#-database-architecture)
8. [API Reference](#-api-reference)
9. [Security Model](#-security-model)
10. [Automated Scheduling System](#-automated-scheduling-system)
11. [PWA — Install on Any Device](#-pwa--install-on-any-device)
12. [Nginx — Production Reverse Proxy](#-nginx--production-reverse-proxy)
13. [Local Development Setup](#-local-development-setup)
14. [Docker Deployment](#-docker-deployment)
15. [AWS EC2 + RDS Production Deployment](#-aws-ec2--rds-production-deployment)
16. [Render.com Cloud Deployment](#-rendercom-cloud-deployment)
17. [Environment Variable Reference](#-environment-variable-reference)
18. [Structured Logging](#-structured-logging)
19. [Project Structure](#-project-structure)
20. [Troubleshooting](#-troubleshooting)

---

## 🎯 What is FaceAttend?

FaceAttend is a production-ready, full-stack biometric attendance platform that replaces physical fingerprint readers, punch cards, and manual registers with a pure-browser face-scan workflow.

**An employee's complete daily flow:**
1. Opens the web app or installed PWA on any device
2. Clicks **Mark Attendance** → camera opens
3. System recognises their face via SFace AI in under 1 second
4. Attendance is timestamped — `present` if on time, `late` if after 9:30 AM IST
5. At 5:00 PM IST, the scheduler auto-marks everyone else `absent`
6. At 5:15 PM IST, each employee receives a daily summary email
7. On the 1st of every month, full monthly reports are generated

**No dedicated hardware required.** Runs entirely in the browser via PWA.

---

## 🏗️ Live System Architecture

### Development / Single-Host Mode

```
Browser / PWA
     │
     │  HTTP (localhost)
     ▼
Flask + Gunicorn (:5000 or :10000)
     │
     ├──► DeepFace SFace Model (preloaded in memory)
     ├──► SQLite file  (attendance_system.db)
     └──► Gmail SMTP (:587)
```

### Recommended Production Architecture (AWS EC2 + RDS)

```
                         ┌──────────────────────────────────────┐
                         │           AWS Cloud (VPC)            │
                         │                                      │
Employee Browser / PWA   │   ┌─────────────────────────────┐   │
       │                 │   │        EC2 Instance           │   │
       │  HTTPS :443     │   │                               │   │
       └────────────────►│   │  ┌─────────────────────────┐ │   │
                         │   │  │  Nginx (TLS termination) │ │   │
                         │   │  │       :443 / :80          │ │   │
                         │   │  └──────────┬────────────────┘ │   │
                         │   │             │ HTTP              │   │
                         │   │             ▼ 127.0.0.1:10000   │   │
                         │   │  ┌──────────────────────────┐  │   │
                         │   │  │    Docker Container       │  │   │
                         │   │  │    Gunicorn + Flask       │  │   │
                         │   │  │                           │  │   │
                         │   │  │   ┌─────────────────┐    │  │   │
                         │   │  │   │  DeepFace SFace  │    │  │   │
                         │   │  │   │  (pre-baked in   │    │  │   │
                         │   │  │   │   Docker image)  │    │  │   │
                         │   │  │   └─────────────────┘    │  │   │
                         │   │  └──────────┬───────────────┘  │   │
                         │   └────────────┬┘                   │   │
                         │                │                     │   │
                         │   ┌────────────▼──────────────────┐ │   │
                         │   │   Amazon RDS (PostgreSQL)      │ │   │
                         │   │        :5432 (private)          │ │   │
                         │   └───────────────────────────────┘ │   │
                         └──────────────────────────────────────┘
                                          │
                                   Gmail SMTP :587
```

### Complete Request Lifecycle (One Attendance Scan)

```
Step 1  Browser captures webcam frame (MediaDevices.getUserMedia API)
Step 2  Frame → Base64 JPEG → POST /api/recognize-face (JSON body)
Step 3  Nginx receives HTTPS → strips TLS → proxy_pass → Gunicorn :10000
Step 4  Flask decodes Base64 → cv2 numpy array (BGR)
Step 5  DeepFace SFace → 128-dimensional float32 embedding vector
Step 6  NumPy L2 distance vs every stored embedding in the database
Step 7  Best match < threshold (12.0) → MATCH FOUND
Step 8  IST timestamp evaluated:
          09:00–09:30 → present
          09:30–17:00 → late
          < 09:00 / > 17:00 → office_closed
          Sunday → office_closed_sunday
Step 9  INSERT into attendance (UNIQUE constraint prevents duplicates)
Step 10 JSON response → browser renders result card with name + status
```

---

## ⚙️ Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Web Framework** | Flask | 3.0.0 | WSGI app, blueprints, routing |
| **WSGI Server** | Gunicorn | 21.2.0 | Production process manager |
| **Reverse Proxy** | Nginx | Latest | TLS termination, port isolation, HTTP→HTTPS |
| **AI / ML** | DeepFace | 0.0.83 | SFace face recognition pipeline |
| **AI Backend** | TensorFlow | 2.12.0 | SFace model inference |
| **Image Processing** | OpenCV (headless) | 4.8.1.78 | Frame decode, resize, face detect |
| **Vector Math** | NumPy | 1.23.5 | L2 Euclidean distance comparison |
| **Primary DB** | PostgreSQL (RDS) | 13+ | Production durable storage |
| **Fallback DB** | SQLite | built-in | Development and auto-failover |
| **DB Driver** | psycopg2-binary | 2.9.9 | PostgreSQL adapter |
| **Auth** | Flask-Login | 0.6.3 | Session management, user loader |
| **Password Hashing** | PBKDF2-HMAC-SHA256 | built-in | 100,000 iterations |
| **Scheduler** | APScheduler | 3.10.4 | Background cron jobs |
| **Email** | Gmail SMTP + STARTTLS | built-in | OTP delivery, daily summaries |
| **Containerisation** | Docker | — | Reproducible build, model pre-baked |
| **Cloud Host** | AWS EC2 + RDS | — | Production deployment target |
| **Cloud Alt.** | Render.com | — | Zero-ops free tier |
| **PWA** | Web App Manifest + Service Worker | — | Installable on any device |
| **Frontend** | Jinja2 + Vanilla JS | — | Server-rendered UI, zero build step |

---

## 🚀 Core Feature Set

### Biometric Attendance

- **Real-time face scan** using device webcam — no additional hardware
- **SFace AI engine** — 28 MB, runs entirely on CPU, no GPU required
- **Sub-second recognition** per frame after model warm-up
- **Duplicate prevention** — `UNIQUE(user_id, date)` constraint prevents marking twice per day
- **Multi-face scene handling** — largest primary face is automatically selected
- **Minimum face area filter** — rejects detections smaller than 40×40 px
- **Business hours enforcement** — attendance locked outside 9:00 AM–5:00 PM IST, Mon–Sat
- **Sunday office-closed lock** — clear error message when office is closed

### User Authentication System

- **Two distinct login portals** — `/auth/login` (employee) and `/auth/admin-login` (admin)
- **Gmail-only registration** — `@gmail.com` enforced at validation layer
- **OTP email verification** — 6-digit code sent via Gmail SMTP before account activation
- **Password reset via OTP** — 4-digit recovery code with configurable expiry and resend throttle
- **OTP rate limiting** — max 5 attempts, 60-second resend cooldown, max 3 resends
- **Strong password policy** — minimum 8 characters, must include letters and numbers
- **PBKDF2-HMAC-SHA256** hashing — 100,000 iterations
- **HttpOnly + Secure session cookies** — XSS-resistant, HTTPS-only in production
- **Configurable session timeout** — default 30 minutes of inactivity
- **Role-Based Access Control (RBAC)** — `admin` and `user` roles with `@role_required` decorator

### Admin Dashboard

- **Live roster** — real-time attendance status for every employee today
- **Full user management** — view, create, and permanently delete employees
- **Per-user attendance history** — paginated, filterable by date range and status
- **Deletion re-authentication** — admin must re-enter their own password before deleting any account
- **Atomic user purge** — deletes user + all attendance records + all audit logs in one transaction
- **Audit log trail** — every significant action persisted to `audit_logs` table

### Employee Dashboard

- **Personal attendance history** — paginated view with status filter
- **Monthly/weekly summary stats** — present, late, absent counts
- **Face registration page** — one-time biometric enrolment with optional re-enrolment
- **Profile picture upload** — stored as base64 in the database
- **Duplicate face guard** — prevents registering a face already claimed by another account

### Automated Scheduling

| Job | Schedule | Action |
|---|---|---|
| `mark_absentees` | 17:00 IST Mon–Sat | Marks every enrolled employee with no check-in as `absent` |
| `send_summaries` | 17:15 IST Mon–Sat | Sends daily attendance summary email to each employee |
| `monthly_reports` | 23:00 IST on 1st of month | Generates monthly attendance reports and audit logs |

### Observability & Logging

- **4 rotating log files** — `application.log`, `attendance.log`, `auth.log`, `errors.log`
- **10 MB / 5 MB** rotating limits with 10 backup generations each
- **Structured format** — `timestamp · name · level · file:line · message`
- **Database audit trail** — `audit_logs` table for `auto_absent_marked`, `monthly_report_generated`, and all admin actions

---

## 🤖 AI Engine: How Face Recognition Works

### Model: SFace (SphereFace variant)

SFace is a lightweight face recognition model optimised for edge and low-resource environments.

| Property | Value |
|---|---|
| Model size | ~28 MB |
| Input | BGR image (any resolution, auto-resized to max 640 px width) |
| Detector backend | OpenCV (fastest option) |
| Embedding dimensions | 128 float32 values |
| Distance metric | **Raw L2 Euclidean distance** (not cosine) |
| Match threshold | `12.0` (configurable via `FACE_RECOGNITION_THRESHOLD`) |
| Same-person distance | typically `0 – 10` |
| Different-person distance | typically `13+` |
| Hardware requirement | CPU only — no GPU needed |

### Registration Pipeline

```
Camera Frame (BGR)
        │
        ▼
Resize to max 640px width (aspect-preserved for speed)
        │
        ▼
DeepFace.represent(model='SFace', detector='opencv', enforce_detection=True)
        │
        ▼
Filter candidates by bounding-box area ≥ 40×40 px
        │
        ▼
Select largest face (primary subject when multiple faces present)
        │
        ▼
np.asarray(embedding, dtype=float32).reshape(-1)   →  128-dim vector
        │
        ▼
Duplicate check: L2 distance against all existing stored embeddings
        │
        ▼
json.dumps(embedding.tolist())  →  stored in users.embedding (TEXT)
```

### Recognition Pipeline

```
Camera Frame (BGR)
        │
        ▼
Same embedding extraction as registration
        │
        ▼
For each enrolled user in database:
    stored  = np.asarray(json.loads(users.embedding), float32)
    distance = np.linalg.norm(stored - query)   ← L2 Euclidean
    track best_distance and best_match
        │
        ▼
if best_distance ≤ threshold (12.0):
    MATCH FOUND → mark_attendance(user_id, IST_timestamp)
else:
    No match — return face_not_recognized
```

### Threshold Auto-Correction

If `FACE_RECOGNITION_THRESHOLD` is set to a value `< 2.0` (cosine-style, e.g. `0.80`), the system automatically resets to `12.0` and logs a warning — preventing silent misconfiguration that would reject all valid matches.

### Cold-Start Optimisation

The SFace model is:
- **Pre-downloaded at Docker build time** (`DeepFace.build_model('SFace')` in Dockerfile) — no delay on first user scan
- **Pre-loaded into memory on app startup** via a background daemon thread — available immediately when the first API call arrives

---

## 🛡️ Liveness Detection & Anti-Spoofing Architecture

To prevent biometric spoofing (e.g., holding up a smartphone screen, displaying a printed photograph, or replaying video streams), FaceAttend incorporates a multi-tiered **Passive + Active Liveness Engine** powered by **MiniFASNet ONNX models** and OpenCV computer vision pipelines.

Attendance registration and verification are gated by this check: a live subject must be confirmed before face embedding extraction and matching are executed.

```
                  Webcam Frame Captured (640x480 @ 85% JPEG)
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │ Layer 1: Anti-Replay Cryptographic Filter         │
             │   - SHA-256 Frame Fingerprint Hashing            │
             │   - Replay window: 30s sliding cache             │
             └────────────────────────┬─────────────────────────┘
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │ Layer 2: Multi-Pass Face Geometry & Alignment    │
             │   - Standard Haar Cascade (minNeighbors=4)       │
             │   - Relaxed Low-Light Fallback (minNeighbors=2)  │
             │   - Center-Bounding Box Spatial Heuristic        │
             └────────────────────────┬─────────────────────────┘
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │ Layer 3: Dual MiniFASNet Deep Ensemble           │
             │   - 2.7x Scale (MiniFASNetV2): Skin Texture/Depth│
             │   - 4.0x Scale (MiniFASNetV1SE): Screen/Borders  │
             │   - Softmax Real-Class Probability (Index 2)     │
             └────────────────────────┬─────────────────────────┘
                                      │
                        ┌─────────────┴─────────────┐
                        │                           │
                 Score ≥ 0.40                  Score ≤ 0.20
                        │                           │
                        ▼                           ▼
                 ✅ PASS: Live Face           ❌ REJECT: Spoof Detected
            (Proceed to SFace Matching)    ("Use live face, not photo/screen")
```

---

### Factors on Which Liveness Detection Depends

The liveness evaluation depends on six key physical, optical, and computational factors:

| Factor | Mechanism / Component | What It Detects / Prevents |
|---|---|---|
| **1. Micro Skin Texture & Light Diffusion** | `MiniFASNetV2.onnx` (2.7× face crop scale) | Examines natural facial skin pores, organic light reflection, micro-shadows, and 3D facial depth. Differentiates biological skin from paper print grain, glossy paper sheen, and flat digital displays. |
| **2. Macro Context & Screen Border Detection** | `MiniFASNetV1SE.onnx` (4.0× context scale) | Inspects the wide surrounding area around the face. Detects smartphone bezels, tablet/monitor frames, physical photograph paper edges, or anomalous backgrounds indicative of presentation attacks. |
| **3. Face Alignment & Detection Robustness** | Multi-pass OpenCV Haar Cascade (`scaleFactor=1.1`, fallback `1.05`) | Detects face region even in varied lighting, tilted head postures, or distant stances. Includes a center-region spatial heuristic aligned with the UI scanning guide to eliminate false detection drops. |
| **4. Optical Resolution & Image Fidelity** | Frontend 640×480 @ 0.85 JPEG compression | High-resolution frame transmission preserves essential fine-grain texture gradients without introducing blocky JPEG macroblock compression artifacts that could degrade AI classification. |
| **5. Anti-Replay Frame Hashing** | SHA-256 fingerprinting (`FRAME_HASH_WINDOW_SECONDS = 30`) | Prevents malicious attackers from capturing an authorized user's live frame once and submitting it repeatedly via script or automated API replay bursts. |
| **6. Active Blink Fallback (Session Burst Mode)** | OpenCV Eye Cascade (`haarcascade_eye.xml`) | Optional multi-frame temporal check for marginal confidence cases. Analyzes sequential eye state (`open → closed → open`) to confirm natural biological blinking. |

---

### Model Classification & Confidence Thresholds

The MiniFASNet ONNX models output 3 distinct probability classes via softmax:
- **Class 0**: Background / Environmental noise
- **Class 1**: Spoof / Presentation Attack (Photo, Screen, Cutout)
- **Class 2**: Real Live Human Face

**Calibrated Decision Boundary:**
- **$\text{Score} \ge 0.40$**: `passive_real` — Instant pass for live users across diverse lighting environments.
- **$\text{Score} \le 0.20$**: `passive_fake` — Immediate rejection for presentation attacks.
- **$0.25 \le \text{Score} < 0.40$**: `passive_marginal_pass` — Soft-pass policy enabling seamless single-glance attendance under challenging webcam conditions without compromising spoof security.

---

## 🗄️ Database Architecture

### Dual-Database with Automatic Failover

The `get_db_connection()` function transparently handles both engines:

```
If DATABASE_URL is set and psycopg2 is installed:
    Try → PostgreSQL (3-second connection timeout)
    On failure → log WARNING "DATABASE AUTO-FALLBACK"
                 switch IS_POSTGRES = False
                 re-initialise SQLite tables if needed
                 continue serving on SQLite

If DATABASE_URL is empty:
    Connect directly to SQLite (30-second busy timeout)
```

This means even if your RDS instance is temporarily unavailable, the application keeps serving traffic on SQLite — zero downtime.

### Schema Overview

**`users`**

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL / INTEGER PK | Auto-increment |
| `username` | VARCHAR(100) UNIQUE | Display name and login key |
| `email` | VARCHAR(255) UNIQUE | Gmail-only enforced |
| `password_hash` | VARCHAR(255) | PBKDF2-HMAC-SHA256 hex |
| `full_name` | VARCHAR(255) | Used in emails and recognition responses |
| `embedding` | TEXT | JSON array of 128 floats (SFace vector) |
| `profile_picture` | TEXT | Base64-encoded image data |
| `role` | VARCHAR(20) | `admin` or `user` |
| `status` | VARCHAR(20) | `active` or `inactive` |
| `is_verified` | INTEGER | 0 = pending OTP, 1 = email verified |
| `created_at` / `updated_at` | TIMESTAMPTZ | UTC timestamps |

**`attendance`**

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL / INTEGER PK | Auto-increment |
| `user_id` | FK → users | `ON DELETE CASCADE` |
| `date` | DATE | IST date of attendance |
| `time_in` | TIME | Actual scan time (IST) |
| `time_out` | TIME | Future extension |
| `status` | VARCHAR(20) | `present`, `late`, `absent`, `half_day` |
| `notes` | TEXT | Admin override notes |
| `marked_by` | VARCHAR(50) | `face_recognition` or `admin` |
| `UNIQUE(user_id, date)` | — | Prevents duplicate daily records |

**`working_hours`** — Per day-of-week schedule (Mon–Sat 09:00–17:00, Sunday closed)

**`pending_verifications`** — OTP registration tokens with expiry, attempt count, resend limits

**`password_reset_otps`** — Password recovery tokens with identical rate-limiting controls

**`audit_logs`** — Immutable append-only event log: `user_id`, `action`, `resource_type`, `resource_id`, `details`, `timestamp`

### Database Indexes (PostgreSQL)

```sql
-- Fast user lookups
CREATE INDEX idx_users_username  ON users(username);
CREATE INDEX idx_users_email     ON users(email);
CREATE INDEX idx_users_role      ON users(role);

-- Efficient range queries for attendance reports
CREATE INDEX idx_attendance_date         ON attendance(date);
CREATE INDEX idx_attendance_user_id      ON attendance(user_id);
CREATE INDEX idx_attendance_date_user    ON attendance(date, user_id);
CREATE INDEX idx_attendance_user_date    ON attendance(user_id, date);
CREATE INDEX idx_attendance_status       ON attendance(status);
```

### Unified SQL Abstraction Layer

The `DBCursorWrapper` class translates SQLite-style `?` placeholders to PostgreSQL-style `%s` at query time — allowing a single codebase to run on both databases without any ORM overhead or query duplication.

---

## 📡 API Reference

All endpoints return JSON. Auth is enforced via Flask-Login session cookies.

### Face Operations

#### `POST /api/register-user`
*(Login required · role: `user` only — admins are exempt)*

Register or update the authenticated user's face biometric.

```json
// Request body
{ "image": "<base64-encoded-jpeg>", "force": false }

// Success — new registration
{ "success": true, "message": "Face biometrics registered successfully for John Doe!" }

// Success — already registered (force=false)
{ "success": true, "already_registered": true, "message": "Face already registered for John Doe. You can now mark attendance!" }

// Error — face belongs to another account
{ "success": false, "message": "This face is already registered to another employee account (Jane Smith)." }

// Error — no face detected
{ "success": false, "message": "No face detected. Look directly at the camera in good lighting." }
```

#### `POST /api/recognize-face`
*(No auth required — designed for kiosk/shared-device use)*

Identify a face in the submitted image and mark attendance.

```json
// Request body
{ "image": "<base64-encoded-jpeg>" }

// Matched and marked
{
  "success": true,
  "found": true,
  "user_id": 42,
  "user_name": "John Doe",
  "user_email": "john@gmail.com",
  "status": "present",
  "marked_at": "2026-09-11 09:15:32",
  "message": "Welcome John Doe! Attendance marked at 2026-09-11 09:15:32 IST"
}

// Not recognised
{ "success": true, "found": false, "code": "face_not_recognized", "message": "..." }
```

**All possible `status` values:**

| Status | Meaning |
|---|---|
| `present` | Scanned 09:00–09:30 IST |
| `late` | Scanned 09:30–17:00 IST |
| `duplicate` | Already marked today |
| `already_absent` | Auto-marked absent by scheduler; contact admin to override |
| `office_closed` | Outside 09:00–17:00 IST window |
| `office_closed_sunday` | Sunday — office closed |
| `admin_exempt` | Admin accounts are not tracked |

### Attendance Data

#### `GET /api/attendance`
*(Login required)*

Paginated personal attendance history. Absent days (Mon–Sat) are synthesised automatically even if no database row exists — so employee and admin views always agree.

| Query Param | Type | Default | Description |
|---|---|---|---|
| `start_date` | YYYY-MM-DD | user registration date | Range start |
| `end_date` | YYYY-MM-DD | today | Range end |
| `status` | string | — | Filter: `present`, `late`, `absent`, `pending` |
| `page` | int | 1 | Page number |
| `page_size` | int | 60 | Records per page |

```json
{
  "success": true,
  "data": [
    { "date": "2026-09-11", "status": "present", "time_in": "09:12:44", "time_out": null, "marked_by": "face_recognition" }
  ],
  "summary": { "present": 18, "late": 2, "absent": 1 },
  "total": 21,
  "page": 1,
  "pages": 1,
  "start_date": "2026-09-01",
  "end_date": "2026-09-11"
}
```

#### `GET /api/users`
All enrolled users (id + display name). No auth guard — used by kiosk UI.

### Admin-Only Endpoints
*(Login required · role: `admin`)*

#### `GET /api/admin/attendance/today`
Live roster — one current-day status per active non-admin employee.

#### `GET /api/admin/attendance/history/<user_id>`
Paginated attendance history for a specific employee. Accepts same query params as `/api/attendance`. Returns `404` if `user_id` not found.

### System

#### `GET /health`
No auth required. Used by Docker, Nginx, load balancers, and uptime monitors.
```json
{ "status": "ok" }
```

---

## 🔐 Security Model

| Concern | Implementation |
|---|---|
| Password storage | PBKDF2-HMAC-SHA256, 100,000 iterations |
| Session cookies | `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SECURE=True` in production |
| Session expiry | Configurable via `SESSION_TIMEOUT_MINUTES` (default 30 min) |
| Email verification | 6-digit OTP required before account activation |
| OTP brute force | Max 5 attempts, 60-second resend cooldown, max 3 resends |
| OTP expiry | 10 minutes (configurable) |
| Duplicate biometrics | L2 distance check against all embeddings before saving |
| Admin account deletion | Requires re-entering admin password — no accidental deletes |
| Port isolation | Gunicorn bound to `127.0.0.1:10000` — never publicly exposed |
| TLS | Nginx terminates all HTTPS — Gunicorn only sees plain HTTP internally |
| Secrets | All credentials in `.env` — never committed, never logged |
| SQL injection | Parameterised queries throughout — no string concatenation in SQL |
| Referential integrity | `ON DELETE CASCADE` — no orphaned attendance records after user deletion |
| Admin exemption | Admin accounts cannot register face biometrics or appear in attendance |

---

## ⏰ Automated Scheduling System

The `APScheduler` `BackgroundScheduler` runs as a daemon thread inside the Gunicorn worker process.

```
APScheduler (daemon thread inside Gunicorn worker)
       │
       ├─ CronTrigger(17:00 IST, Mon–Sat) ──► mark_end_of_day_absentees()
       │       └─ For each enrolled user with no attendance row today:
       │              INSERT attendance(status='absent', marked_by='scheduler')
       │              log_audit(user_id, action='auto_absent_marked', ...)
       │
       ├─ CronTrigger(17:15 IST, Mon–Sat) ──► send_daily_summaries()
       │       └─ For each today's record with a valid email:
       │              email_service.send_daily_summary(user_id, email, name, data)
       │
       └─ CronTrigger(day=1, 23:00 IST) ──► generate_monthly_reports()
               └─ For each user:
                      report = get_user_monthly_summary(user_id, year, month)
                      log_audit(user_id, action='monthly_report_generated',
                                details=f'{present} present, {absent} absent, {late} late')
```

**Duplicate-start guard:** `start_scheduler()` checks `scheduler.get_job('mark_absentees')` before registering any job — safe to call on every app restart.

---

## 📱 PWA — Install on Any Device

FaceAttend is a full Progressive Web App. Users install it to their home screen without an App Store.

**Capabilities:**
- **Installable** — `manifest.json` with `display: standalone`
- **Offline-ready** — Service Worker (`/sw.js`) caches core assets with cache-first strategy
- **App shortcuts** — "Mark Attendance" (`/camera`) and "My Reports" (`/report`) shortcuts on long-press
- **Maskable icons** — Adaptive icon format for Android home screens
- **Theme colour** — `#2563eb` matches the UI chrome

**How to install:**
- **Chrome / Edge (desktop):** Click the install icon in the address bar
- **Chrome (Android):** Browser menu → "Add to Home screen"
- **Safari (iOS):** Share button → "Add to Home Screen"

**Technical detail:** The Service Worker is served from `/sw.js` (root path) with header `Service-Worker-Allowed: /` to grant full-origin scope control.

---

## 🌐 Nginx — Production Reverse Proxy

### Role in the Stack

Nginx is the **only publicly exposed process** in production. It provides:

1. **TLS / HTTPS termination** — decrypts incoming HTTPS; Gunicorn sees plain HTTP internally
2. **HTTP → HTTPS forced redirect** — required because browsers refuse webcam access on non-HTTPS origins
3. **Port isolation** — Gunicorn binds to `127.0.0.1:10000` (loopback) and is invisible to the internet
4. **Header forwarding** — real client IP passed via `X-Real-IP` and `X-Forwarded-For` for logging and rate-limiting
5. **Large body support** — `client_max_body_size 10M` allows webcam frame uploads

### Why HTTPS is Non-Negotiable

Modern browsers enforce the **Secure Context** requirement for `MediaDevices.getUserMedia()` (the webcam API). Without HTTPS, the camera permission prompt will **never appear**. The only exception is `localhost`, which is why local development works without TLS.

### Traffic Flow

```
Public Internet (port 443)
        │
        ▼
  Nginx on EC2
  (TLS termination)
        │
        │  HTTP 127.0.0.1:10000
        │  (loopback — never leaves the server)
        ▼
  Docker / Gunicorn
        │
        ▼
  Flask Application
```

### Complete Nginx Configuration

Save as `/etc/nginx/sites-available/faceattend`:

```nginx
# ── HTTP: redirect all traffic to HTTPS ──────────────────────────
server {
    listen 80;
    server_name attendance.your-domain.com;

    return 301 https://$host$request_uri;
}

# ── HTTPS: TLS termination + reverse proxy ───────────────────────
server {
    listen 443 ssl http2;
    server_name attendance.your-domain.com;

    # TLS certificates (Certbot populates these automatically)
    ssl_certificate     /etc/letsencrypt/live/attendance.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/attendance.your-domain.com/privkey.pem;

    # Modern TLS settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options    nosniff                               always;
    add_header X-Frame-Options           SAMEORIGIN                            always;
    add_header X-XSS-Protection         "1; mode=block"                       always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin"     always;

    # Allow webcam frame uploads (Base64 JPEG can be several MB)
    client_max_body_size 10M;

    location / {
        proxy_pass         http://127.0.0.1:10000;
        proxy_http_version 1.1;

        # Pass real client information through to Flask
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 90s;
        proxy_connect_timeout 10s;
    }
}
```

### Install and Enable

```bash
# 1. Install Nginx
sudo apt update && sudo apt install -y nginx

# 2. Write config (paste the block above)
sudo nano /etc/nginx/sites-available/faceattend

# 3. Enable the site
sudo ln -s /etc/nginx/sites-available/faceattend /etc/nginx/sites-enabled/faceattend

# 4. Test syntax
sudo nginx -t

# 5. Reload without downtime
sudo systemctl reload nginx

# 6. Get a free TLS certificate from Let's Encrypt
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d attendance.your-domain.com

# 7. Verify auto-renewal
sudo certbot renew --dry-run
```

### Nginx Quick Reference

| Command | Purpose |
|---|---|
| `sudo nginx -t` | Validate configuration syntax |
| `sudo systemctl reload nginx` | Apply config changes (zero downtime) |
| `sudo systemctl status nginx` | Check running state |
| `sudo tail -f /var/log/nginx/error.log` | Stream error logs |
| `sudo tail -f /var/log/nginx/access.log` | Stream access logs |

---

## 💻 Local Development Setup

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10.x (3.10.13 recommended) |
| pip | 23+ |
| Git | any |
| Webcam | Required for face features |

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/face-attendance-deepface.git
cd face-attendance-deepface

# 2. Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install all dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env → set ADMIN_EMAIL, ADMIN_PASSWORD, and SMTP_* credentials

# 5. Start the application
python run.py
```

Open **http://localhost:5000** in your browser.

**First-time startup checklist:**
- Database tables are auto-created on first run
- Default admin account bootstrapped from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`
- SFace model pre-loads in a background thread — look for `SFace model preloaded successfully` in the console
- Camera works on localhost without HTTPS (browser secure context exception)

**Development tips:**
- Set `SCHEDULER_ENABLED=false` to disable background cron jobs during dev
- Logs are written to `logs/` directory in the project root
- SQLite database created at `attendance_system.db` by default

---

## 🐳 Docker Deployment

### What the Docker Image Contains

```dockerfile
FROM python:3.10.13-slim           # Pinned Python for TensorFlow compatibility

# System libs: OpenCV needs libgl1, libglib2.0-0
RUN apt-get install build-essential cmake libgl1 libglib2.0-0

# Install Python dependencies
RUN pip install -r requirements.txt

# ← Key: pre-download SFace model during build, not at runtime
RUN python -c "from deepface import DeepFace; DeepFace.build_model('SFace')"

EXPOSE 10000
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 run:app"]
```

The SFace model is baked into the image — no cold-start download on first user scan.

### Build and Run

```bash
# Build image
docker build -t faceattend:latest .

# Create persistent host directories
mkdir -p data logs

# Start container (loopback-only binding for security)
docker run -d \
  --name faceattend \
  --restart unless-stopped \
  -p 127.0.0.1:10000:10000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  faceattend:latest

# Verify healthy startup
curl http://127.0.0.1:10000/health
# Expected: {"status":"ok"}

# Stream startup logs
docker logs -f faceattend
```

> **Security note:** `-p 127.0.0.1:10000:10000` binds to loopback only. The container port is invisible to the internet. Nginx on the host handles all public HTTPS traffic.

### Container Lifecycle

```bash
docker stop faceattend        # Graceful shutdown
docker start faceattend       # Restart existing container
docker rm faceattend          # Remove container (volumes persist on host)
docker logs --tail 200 faceattend   # Last 200 log lines
```

### Zero-Downtime Update

```bash
cd /opt/faceattend/app-source
git pull origin main

# Rebuild image
docker build -t faceattend:latest .

# Swap container
docker stop faceattend && docker rm faceattend

docker run -d \
  --name faceattend \
  --restart unless-stopped \
  --env-file /opt/faceattend/.env \
  -p 127.0.0.1:10000:10000 \
  -v /opt/faceattend/data:/app/data \
  -v /opt/faceattend/logs:/app/logs \
  faceattend:latest

curl http://127.0.0.1:10000/health
```

---

## ☁️ AWS EC2 + RDS Production Deployment

### Recommended Infrastructure

| Component | AWS Service | Notes |
|---|---|---|
| Application host | EC2 (t3.medium+) | Docker + Nginx |
| Database | RDS for PostgreSQL 13+ | Same VPC as EC2, private subnet |
| Persistent storage | EBS (attached to EC2) | Mount `/app/data` and `/app/logs` |
| TLS | Let's Encrypt via Certbot | Free, auto-renews every 90 days |
| DNS | Route 53 or external registrar | A record pointing to EC2 Elastic IP |

### Security Group Rules

| Resource | Protocol | Port | Source |
|---|---|---|---|
| EC2 | TCP | 22 (SSH) | Your fixed admin IP only |
| EC2 | TCP | 80 (HTTP) | `0.0.0.0/0` (redirects to HTTPS) |
| EC2 | TCP | 443 (HTTPS) | `0.0.0.0/0` |
| RDS | TCP | 5432 | **EC2 security group ID** — never `0.0.0.0/0` |

### Step 1: Create RDS PostgreSQL Instance

- Place in the same VPC and availability zone as your EC2 instance
- Choose a **private subnet** — disable public access
- Enable automated backups with at least 7-day retention
- Create a dedicated database user for FaceAttend (not the RDS master user)
- Note the endpoint URL, database name, username, and password for `DATABASE_URL`

### Step 2: Prepare EC2

```bash
# Install Docker using the official script
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# Set up project directory layout
sudo mkdir -p /opt/faceattend/{app-source,data,logs}
sudo git clone https://github.com/your-org/face-attendance-deepface.git /opt/faceattend/app-source

# Create production secrets file (mode 600 — owner-only read)
sudo nano /opt/faceattend/.env
sudo chmod 600 /opt/faceattend/.env
```

### Step 3: Production `.env`

```dotenv
FLASK_ENV=production
SECRET_KEY=generate-a-64-character-random-string-here
PORT=10000

# Amazon RDS PostgreSQL
DATABASE_URL=postgresql://attendance_user:URL_ENCODED_PASSWORD@your-rds-endpoint.rds.amazonaws.com:5432/faceattend
DB_PATH=/app/data/attendance_system.db    # SQLite auto-fallback path

SCHEDULER_ENABLED=true
FACE_RECOGNITION_THRESHOLD=12.0
SESSION_TIMEOUT_MINUTES=30

ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=change-this-to-a-strong-password-before-first-start
ADMIN_FULL_NAME=System Administrator

SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sender@gmail.com
SMTP_PASSWORD=GMAIL_16_CHARACTER_APP_PASSWORD
SMTP_FROM=sender@gmail.com
SMTP_USE_TLS=true
SMTP_TIMEOUT_SECONDS=10

OTP_EXPIRES_MINUTES=10
OTP_MAX_ATTEMPTS=5
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_RESENDS=3
```

> If the RDS password contains `@`, `:`, `/`, or `#`, URL-encode those characters in `DATABASE_URL`.

### Step 4: Build and Start Container

```bash
cd /opt/faceattend/app-source
docker build -t faceattend:latest .

docker run -d \
  --name faceattend \
  --restart unless-stopped \
  --env-file /opt/faceattend/.env \
  -p 127.0.0.1:10000:10000 \
  -v /opt/faceattend/data:/app/data \
  -v /opt/faceattend/logs:/app/logs \
  faceattend:latest

# Verify
curl http://127.0.0.1:10000/health
docker logs --tail 100 faceattend
```

If RDS is reachable, startup logs will show successful PostgreSQL initialisation. If RDS is unreachable, you will see the auto-fallback warning and the application runs on SQLite until RDS recovers.

### Step 5: Install Nginx + TLS

```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx

# Write Nginx config (see the Nginx section above)
sudo nano /etc/nginx/sites-available/faceattend
sudo ln -s /etc/nginx/sites-available/faceattend /etc/nginx/sites-enabled/faceattend
sudo nginx -t
sudo systemctl reload nginx

# Free TLS certificate
sudo certbot --nginx -d attendance.your-domain.com
```

### Step 6: Validate End-to-End

```bash
# Health check over HTTPS
curl https://attendance.your-domain.com/health

# In browser
# 1. Confirm green padlock
# 2. Log in at /auth/admin-login with bootstrapped admin credentials
# 3. Create a test employee and verify OTP email delivery
# 4. Log in as employee → Register Face → Mark Attendance
# 5. Confirm employee dashboard and admin live roster show the same status
# 6. Confirm RDS automated backup policy is active
```

### Updating an Existing AWS EC2 Server

Run these commands on the EC2 instance after pushing new changes to GitHub. This procedure keeps production secrets in `/opt/faceattend/.env` and keeps the database and logs in their existing host volumes.

```bash
cd /opt/faceattend/app-source

# Confirm the server is on the expected branch and has no local changes
git status
git branch --show-current

# Download and apply only fast-forward changes from GitHub
git fetch origin
git pull --ff-only origin main

# Keep the currently running image available for rollback if needed
docker tag faceattend:latest faceattend:previous

# Rebuild the image so Python dependency and application changes are included
docker build -t faceattend:latest .

# Replace the running container; /opt/faceattend/data and /opt/faceattend/logs persist
docker stop faceattend
docker rm faceattend
docker run -d \
  --name faceattend \
  --restart unless-stopped \
  --env-file /opt/faceattend/.env \
  -p 127.0.0.1:10000:10000 \
  -v /opt/faceattend/data:/app/data \
  -v /opt/faceattend/logs:/app/logs \
  faceattend:latest

# Verify the new container and application
docker ps --filter name=faceattend
curl http://127.0.0.1:10000/health
docker logs --tail 100 faceattend
```

If `git status` reports local changes, stop and review them before pulling. If the new container fails, inspect `docker logs faceattend`, then restore the previous image by replacing `faceattend:latest` with `faceattend:previous` in the `docker run` command. Do not delete `/opt/faceattend/data` or `/opt/faceattend/logs` during an update.

#### Fix GitHub `Permission denied (publickey)` on EC2

The deployment script uses the repository's SSH remote (`git@github.com:...`). If GitHub rejects the key, the code pull failed and the script must not be treated as a successful deployment. Configure a read-only deploy key for the repository:

```bash
# Run on the EC2 instance as the ubuntu user
ssh-keygen -t ed25519 -C "faceattend-ec2" -f ~/.ssh/id_ed25519_github
cat ~/.ssh/id_ed25519_github.pub
```

Copy the printed public key into GitHub: **Repository → Settings → Deploy keys → Add deploy key**. Leave **Allow write access** disabled because the server only needs to pull code.

Then configure and test the key:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
ssh-keyscan github.com >> ~/.ssh/known_hosts
ssh -T git@github.com
```

After GitHub accepts the key, update the application:

```bash
cd /home/ubuntu/face-attendance-deepface
git pull --ff-only origin main
sudo bash /home/ubuntu/deploy-face-attendance.sh
curl http://127.0.0.1:10000/health
```

The deployment script should use `set -e` or `set -euo pipefail` near its beginning so a failed `git pull` stops the deployment before Docker is rebuilt or restarted.

---

## 🚀 Render.com Cloud Deployment

For zero-ops hosting without managing servers, deploy directly to [Render.com](https://render.com) using the included `render.yaml`.

```yaml
services:
  - type: web
    name: face-attendance
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn run:app --timeout 120 --workers 1
    envVars:
      - key: FLASK_ENV
        value: production
      - key: FACE_RECOGNITION_THRESHOLD
        value: "12.0"
      - key: SECRET_KEY
        generateValue: true        # Render generates a cryptographically random value
      - key: ADMIN_EMAIL
        sync: false                # Set manually in Render dashboard
      - key: ADMIN_PASSWORD
        sync: false                # Set manually in Render dashboard
      - key: PYTHON_VERSION
        value: 3.10.13
```

**Steps:**
1. Fork this repository to your GitHub account
2. Go to [render.com](https://render.com) → **New** → **Web Service** → connect your fork
3. Render detects `render.yaml` automatically
4. Set `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `SMTP_*` in the Render Environment dashboard
5. Click **Deploy**

> **Free tier note:** Render free tier spins down after 15 minutes of inactivity. The SFace model loads on cold start (~30–60 seconds). Consider a paid plan for production use.

---

## 🔧 Environment Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `FLASK_ENV` | No | `development` | Set to `production` to enable secure cookies |
| `SECRET_KEY` | **Yes** | insecure dev string | Flask session signing key — generate 64+ random characters |
| `PORT` | No | `5000` | Port Gunicorn binds to |
| `DATABASE_URL` | No | — | PostgreSQL connection string; empty = use SQLite |
| `DB_PATH` | No | `/app/data/attendance_system.db` | SQLite path (also used as RDS fallback) |
| `SCHEDULER_ENABLED` | No | `true` | Set `false` to disable background cron jobs |
| `FACE_RECOGNITION_THRESHOLD` | No | `12.0` | SFace L2 distance threshold (valid range: 2.0–50.0) |
| `SESSION_TIMEOUT_MINUTES` | No | `30` | Session inactivity timeout |
| `ADMIN_USERNAME` | No | `admin` | Bootstrap admin login username |
| `ADMIN_EMAIL` | **Yes** | — | Bootstrap admin email address |
| `ADMIN_PASSWORD` | **Yes** | — | Bootstrap admin password |
| `ADMIN_FULL_NAME` | No | — | Bootstrap admin display name |
| `SMTP_ENABLED` | No | `false` | Enable Gmail SMTP for OTPs and summaries |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port (STARTTLS) |
| `SMTP_USERNAME` | Conditional | — | Sender Gmail address (required if SMTP_ENABLED=true) |
| `SMTP_PASSWORD` | Conditional | — | Gmail **App Password** — NOT your Google account password |
| `SMTP_FROM` | Conditional | — | Sender address shown in email From header |
| `SMTP_USE_TLS` | No | `true` | Enable STARTTLS |
| `SMTP_TIMEOUT_SECONDS` | No | `10` | SMTP connection timeout |
| `OTP_EXPIRES_MINUTES` | No | `10` | OTP validity window |
| `OTP_MAX_ATTEMPTS` | No | `5` | Max wrong OTP submissions before lockout |
| `OTP_RESEND_COOLDOWN_SECONDS` | No | `60` | Minimum seconds between resend requests |
| `OTP_MAX_RESENDS` | No | `3` | Maximum OTP resend requests per session |

### Gmail App Password Setup

Gmail requires an **App Password** (not your Google account password) for programmatic SMTP:

1. Enable **2-Step Verification** on your Gmail account
2. Visit **Google Account → Security → App passwords**
3. Create a new App Password (select "Mail" and "Other device")
4. Copy the 16-character generated code
5. Set it as `SMTP_PASSWORD` in your `.env`

---

## 📊 Structured Logging

Four separate rotating log files are written to the `logs/` directory:

| File | Level | Max Size | Backups | Content |
|---|---|---|---|---|
| `application.log` | DEBUG | 10 MB | 10 | All application events (most verbose) |
| `attendance.log` | INFO | 5 MB | 10 | Attendance mark, recognition, absent-marking |
| `auth.log` | INFO | 5 MB | 10 | Login, OTP requests, registration, password reset |
| `errors.log` | ERROR | 5 MB | 10 | Exceptions and critical failures |

**Log line format:**
```
2026-09-11 09:15:32 - face_service - INFO - [face_service.py:197] - SFace comparison user_id=42 distance=8.231 threshold=12.0
2026-09-11 09:15:32 - face_service - INFO - [face_service.py:209] - Face MATCHED user_id=42 distance=8.231
```

**Live log monitoring:**
```bash
# All application events
tail -f logs/application.log

# Authentication events only
tail -f logs/auth.log

# Docker container stdout/stderr
docker logs -f faceattend

# Nginx access log
sudo tail -f /var/log/nginx/access.log
```

---

## 📁 Project Structure

```
face-attendance-deepface/
├── app/
│   ├── __init__.py               # App factory: Flask, blueprints, scheduler, model preload
│   ├── models/
│   │   └── db.py                 # Entire data layer: schema DDL, CRUD, dual-DB wrapper (~1900 lines)
│   ├── routes/
│   │   ├── auth.py               # Login, register, OTP, password reset, RBAC decorators
│   │   ├── api.py                # REST API: face register, face recognize, attendance history
│   │   └── views.py              # Page routes, PWA service worker/manifest, error handlers
│   ├── services/
│   │   ├── face_service.py       # SFace embedding extraction + L2 recognition engine
│   │   ├── email_service.py      # Gmail SMTP — OTP delivery (registration + password reset)
│   │   └── scheduler.py          # APScheduler: absent marking, daily summaries, monthly reports
│   ├── utils/
│   │   ├── logging_config.py     # 4-stream rotating log setup
│   │   └── helpers.py            # base64_to_cv2 decoder utility
│   ├── templates/
│   │   ├── base.html             # Shared layout with PWA meta tags
│   │   ├── index.html            # Employee dashboard (attendance stats + history)
│   │   ├── camera.html           # Live face scanner (webcam + attendance marking)
│   │   ├── register.html         # One-time face registration / re-registration
│   │   ├── report.html           # Full attendance history with charts
│   │   ├── admin/
│   │   │   ├── dashboard.html    # Admin live roster (async-loaded)
│   │   │   └── users.html        # User management: view, delete employees
│   │   └── auth/
│   │       └── login.html        # Unified login template (user mode + admin mode)
│   └── static/
│       ├── manifest.json         # PWA manifest (installable, shortcuts, maskable icons)
│       ├── sw.js                 # Service Worker (cache-first offline support)
│       ├── css/                  # Stylesheets
│       ├── js/                   # Client-side JavaScript
│       └── img/                  # Logo and PWA icons
├── Dockerfile                    # Python 3.10.13-slim, SFace pre-baked, Gunicorn entrypoint
├── render.yaml                   # Render.com one-click deploy configuration
├── Procfile                      # Heroku/Render process file
├── requirements.txt              # All Python dependencies (pinned versions)
├── run.py                        # Application entry point (calls create_app())
├── .env.example                  # Template for all environment variables
└── .dockerignore                 # Excludes venv, .env, logs, __pycache__ from Docker context
```

---

## 🔍 Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `/health` not returning `{"status":"ok"}` | Container not running or wrong port | `docker ps` · `docker logs faceattend` · check `PORT=10000` in `.env` |
| `502 Bad Gateway` from Nginx | Container stopped or bound to wrong address | Check `docker ps` · ensure `-p 127.0.0.1:10000:10000` · verify `proxy_pass http://127.0.0.1:10000` in Nginx |
| Camera permission denied | Page not served over HTTPS | Set up Nginx + Certbot TLS; `localhost` is the only non-HTTPS exception |
| "Face not recognized" despite correct person | Threshold too tight, poor lighting, or bad registration | Brighter lighting; re-register face; verify `FACE_RECOGNITION_THRESHOLD=12.0` |
| "Invalid FACE_RECOGNITION_THRESHOLD" in logs | Value set to cosine-style (e.g. `0.80`) | Set to `12.0` — SFace uses L2 Euclidean distance, not cosine similarity |
| OTP email never arrives | SMTP not configured or wrong App Password | Check `SMTP_ENABLED=true` · verify `SMTP_PASSWORD` is a 16-char App Password · check `logs/auth.log` |
| `DATABASE AUTO-FALLBACK` warning in logs | RDS unreachable | Check EC2→RDS security group allows TCP 5432 · verify RDS endpoint, credentials, and that instance is running |
| API returns 503 "Face AI engine is initializing" | Container just started; model still loading | Wait 15–30 seconds after container start and retry |
| `psycopg2` ImportError | psycopg2-binary not installed | `pip install psycopg2-binary==2.9.9` or rebuild Docker image |
| Scheduler running duplicate jobs | Two processes started simultaneously | Use `--workers 1` with Gunicorn · set `SCHEDULER_ENABLED=false` in dev |
| Employee and admin attendance views disagree | Stale browser cache | Hard refresh (Ctrl+Shift+R) · both views use identical `get_user_attendance_history()` query |

---

<div align="center">

Built with 🧠 DeepFace SFace · 🐍 Flask 3 · 🐳 Docker · 🌐 Nginx · ☁️ AWS EC2 + RDS · 📱 PWA

</div>


~/deploy-face-attendance.sh // command to redeploy the project on aws server after making changes
