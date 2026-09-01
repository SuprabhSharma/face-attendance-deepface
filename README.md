# FaceAttend

### AI-powered biometric attendance for teams, classrooms, and modern workplaces

[![Python](https://img.shields.io/badge/Python-3.10.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![DeepFace](https://img.shields.io/badge/DeepFace-SFace-FF6F00?style=flat-square)](https://github.com/serengil/deepface)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-336791?style=flat-square)](https://www.postgresql.org/)
[![Live application](https://img.shields.io/badge/Live%20Application-faceattend--live.duckdns.org-0d7a6a?style=flat-square&logo=googlechrome&logoColor=white)](https://faceattend-live.duckdns.org/)

**[Open the live application](https://faceattend-live.duckdns.org/)**

FaceAttend is a Flask-based attendance platform that lets employees enroll their face once and mark attendance with a camera scan. It combines SFace face embeddings, role-based access, Gmail OTP verification, attendance reports, an administrator dashboard, a progressive web app experience, and deployment options ranging from a local SQLite file to a production EC2 + Amazon RDS architecture.

> **Privacy notice:** face embeddings are biometric data. Deploy this application only with appropriate consent, retention, access-control, and workplace or educational privacy policies.

---

## Contents

- [What the application provides](#what-the-application-provides)
- [Application flow](#application-flow)
- [Recognition and attendance rules](#recognition-and-attendance-rules)
- [Architecture](#architecture)
- [Database modes](#database-modes)
- [Technology stack](#technology-stack)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Run locally with SQLite](#run-locally-with-sqlite)
- [Run with Docker](#run-with-docker)
- [Deploy to AWS EC2 with Amazon RDS](#deploy-to-aws-ec2-with-amazon-rds)
- [Configuration reference](#configuration-reference)
- [Routes and API](#routes-and-api)
- [Database schema](#database-schema)
- [Operations and maintenance](#operations-and-maintenance)
- [Security and privacy checklist](#security-and-privacy-checklist)
- [Troubleshooting](#troubleshooting)
- [Limitations and roadmap](#limitations-and-roadmap)

---

## What the application provides

| Area | Capability |
| --- | --- |
| Face enrollment | One-time SFace enrollment, duplicate-face protection, and re-registration when an embedding needs to be refreshed |
| Attendance | Camera-based recognition with one attendance record per employee per day |
| Status logic | present, late, half_day, absent, and live pending status |
| Employee experience | Dashboard, camera terminal, attendance history, reports, profile, password change, and PWA installation |
| Administrator experience | Separate admin login, live roster, status counts, enrollment visibility, employee management, and individual attendance history |
| Account security | Gmail-only email verification, hashed OTPs, expiry, attempt limits, resend throttling, and employee password recovery |
| Data storage | SQLite for local/single-host deployments or PostgreSQL through DATABASE_URL for Amazon RDS |
| Deployment | Python, Gunicorn, Docker, Nginx-compatible reverse proxy, Render configuration, EC2, and RDS |
| Operations | Health endpoint, rotating application/auth/attendance/error logs, automatic absent marking, and monthly report generation |

---

## Application flow

### Employee onboarding

~~~text
Open registration
      |
      v
Enter name, Gmail address, and password
      |
      v
Receive six-digit Gmail OTP
      |
      v
Verify OTP  ------ invalid/expired ------> request a new OTP
      |
      v
Account is created
      |
      v
Sign in and register a face
      |
      v
Use the camera to mark attendance
      |
      v
View dashboard, reports, and attendance history
~~~

An employee account is not created until the registration OTP is verified. Passwords must be at least eight characters and contain both letters and numbers. The current application accepts Gmail addresses (@gmail.com) for employee registration and recovery.

### Daily attendance

1. The browser captures a camera frame and sends it to the recognition endpoint.
2. DeepFace detects a face and generates an SFace embedding.
3. FaceAttend compares that embedding with enrolled employee embeddings.
4. The best match is accepted only when its Euclidean L2 distance is within the configured threshold.
5. The application creates at most one attendance record for that employee on that date.
6. The dashboard and administrator roster resolve the status using the same business rules.

### Administrator workflow

Administrators use the dedicated /auth/admin-login page. An administrator can inspect live attendance, see whether an employee is enrolled, review history, and manage employee accounts. Administrators are intentionally exempt from face enrollment and attendance tracking.

---

## Recognition and attendance rules

### Face recognition

The application currently uses:

- **Model:** DeepFace SFace
- **Detector:** OpenCV
- **Comparison:** raw Euclidean L2 distance
- **Default threshold:** 12.0
- **Minimum accepted detected face area:** 40 x 40 pixels
- **Multiple faces:** the largest valid face is selected
- **Image processing:** large frames are downscaled to a maximum width of 640 pixels

The threshold is a distance, not a cosine similarity score. Values below 2.0 are treated as likely cosine-style configuration and automatically replaced with the SFace default. Thresholds above 50 are also rejected and replaced with the default.

Recognition accuracy depends on lighting, camera quality, face angle, distance from the camera, and the threshold chosen for the environment. Test with representative users before production rollout.

### Current attendance policy

The business policy in the code is based on India Standard Time (IST), Monday through Saturday:

| Scan time | Result |
| --- | --- |
| 06:00–09:15 | present |
| 09:16–13:00 | late |
| 13:01–17:00 | half_day |
| Before 06:00 | Rejected; the device is not open |
| After 17:00 | Rejected; the device is locked |
| Sunday | Rejected; weekly office closure |
| No scan on a previous workday | absent |
| No scan today before 17:00 | pending in live views |

The application stores physical attendance rows and synthesizes missing Monday–Saturday rows in report/history views so employee and administrator screens remain consistent.

> **Scheduler timezone note:** attendance calculations use IST, but the scheduler jobs are declared as 17:00 and 17:15 triggers. Before production use, confirm the EC2/container process timezone or explicitly update the scheduler configuration so automatic jobs run at the intended local time.

---

## Architecture

### Local or single-host deployment

~~~mermaid
flowchart LR
    B[Employee browser / PWA] -->|HTTP or HTTPS| F[Flask + Gunicorn]
    F --> AI[DeepFace SFace]
    F --> DB[(SQLite file)]
    F --> SMTP[Gmail SMTP]
~~~

This mode is ideal for development, demos, classrooms, or one small office on one host. The SQLite file must live on persistent storage and must not be shared by multiple application hosts.

### Recommended AWS deployment

~~~mermaid
flowchart LR
    U[Employee browser / PWA] -->|HTTPS :443| N[Nginx reverse proxy]
    N -->|localhost :10000| E[EC2 Docker container]
    E --> AI[DeepFace SFace model]
    E --> R[(Amazon RDS for PostgreSQL)]
    E --> L[(EBS-backed logs / fallback SQLite)]
    E --> M[Gmail SMTP :587]
~~~

The recommended production shape is one EC2 application host, Nginx for TLS termination, and a private RDS PostgreSQL instance for durable application data. The container includes the SFace model during the image build, which avoids downloading it during a user's first scan.

---

## Database modes

FaceAttend selects the database at startup based on DATABASE_URL.

| Mode | Enable with | Best for | Important considerations |
| --- | --- | --- | --- |
| SQLite | Set DB_PATH; leave DATABASE_URL empty | Local development, testing, one host | Use a persistent disk. SQLite is not suitable as a shared multi-instance production database. |
| PostgreSQL / Amazon RDS | Set DATABASE_URL=postgresql://... | EC2 production, durable backups, future horizontal growth | Keep RDS private, permit port 5432 only from the EC2 security group, and monitor connection health. |

### How selection and fallback work

1. If DATABASE_URL is present and psycopg2 is installed, the application attempts PostgreSQL.
2. If the PostgreSQL connection cannot be established, the current code falls back to SQLite at DB_PATH.
3. The fallback is a **continuity mechanism, not replication**.
4. Data written to SQLite while RDS is unavailable is not automatically copied back to RDS.

For a production EC2 deployment, verify the RDS network path before sending traffic to the application. If fallback is intentionally enabled, mount /app/data to persistent EBS storage and monitor logs closely so a temporary database failure does not silently create two data sets.

The database schema is initialized automatically at application startup. This repository does not currently include Alembic or another versioned migration system; back up the database and test schema changes before upgrading a live deployment.

---

## Technology stack

| Layer | Technology |
| --- | --- |
| Runtime | Python 3.10.13 |
| Web framework | Flask 3.0, Jinja2 |
| Authentication | Flask-Login, PBKDF2-HMAC password hashing |
| Computer vision | OpenCV, Pillow |
| Face AI | DeepFace with SFace |
| Database drivers | Built-in SQLite and psycopg2-binary for PostgreSQL |
| Scheduling | APScheduler |
| Email | Gmail SMTP with STARTTLS |
| Production server | Gunicorn |
| Packaging | Docker |
| Frontend delivery | Server-rendered templates, JavaScript, responsive CSS, PWA manifest, service worker |

---

## Project structure

~~~text
face-attendance-deepface/
├── app/
│   ├── __init__.py                 # Flask application factory and startup hooks
│   ├── models/
│   │   └── db.py                   # SQLite/PostgreSQL adapter, schema, attendance logic
│   ├── routes/
│   │   ├── auth.py                 # Login, registration, OTP, recovery, profile
│   │   ├── api.py                  # Recognition, attendance, and admin APIs
│   │   └── views.py                # HTML pages and PWA assets
│   ├── services/
│   │   ├── face_service.py         # SFace embeddings and matching
│   │   ├── email_service.py        # Gmail SMTP delivery
│   │   └── scheduler.py            # Absent marking and report jobs
│   ├── static/                     # CSS, JavaScript, icons, manifest, service worker
│   └── templates/                  # Employee, auth, and administrator screens
├── clear_attendance.py             # Admin-authenticated attendance purge utility
├── Dockerfile                      # Python 3.10 image with SFace model preloaded
├── Procfile                        # Gunicorn process declaration
├── render.yaml                     # Render deployment configuration
├── requirements.txt                # Pinned Python dependencies
├── run.py                          # Local entry point and Gunicorn app object
├── .env.example                    # Safe configuration template
└── README.md
~~~

---

## Prerequisites

For local development:

- Python **3.10.13**
- Git
- A browser with camera permissions
- A Gmail account with 2-Step Verification and an App Password if employee registration or password recovery is enabled

For Docker or AWS:

- Docker Engine and Docker Compose-compatible tooling if you add Compose yourself
- An EC2 host with enough memory for TensorFlow and DeepFace
- For RDS mode: a PostgreSQL RDS instance, its endpoint, credentials, and security-group connectivity
- For camera access outside localhost: a valid HTTPS certificate and domain name

---

## Run locally with SQLite

### 1. Clone and enter the project

~~~bash
git clone https://github.com/SuprabhSharma/face-attendance-deepface.git
cd face-attendance-deepface
~~~

### 2. Create a Python environment

macOS/Linux:

~~~bash
python3.10 -m venv venv
source venv/bin/activate
~~~

Windows PowerShell:

~~~powershell
py -3.10 -m venv venv
.\venv\Scripts\Activate.ps1
~~~

### 3. Install dependencies

~~~bash
python -m pip install --upgrade pip
pip install -r requirements.txt
~~~

### 4. Create environment configuration

macOS/Linux:

~~~bash
cp .env.example .env
~~~

Windows PowerShell:

~~~powershell
Copy-Item .env.example .env
~~~

For a basic local SQLite run, set at least:

~~~dotenv
FLASK_ENV=development
SECRET_KEY=replace-with-a-long-random-value
DB_PATH=attendance_system.db
DATABASE_URL=
SCHEDULER_ENABLED=false
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace-with-a-strong-password
FACE_RECOGNITION_THRESHOLD=12.0
~~~

If employees need to register or recover a password, configure Gmail SMTP as described in the [configuration reference](#configuration-reference). Without SMTP, those email-based flows cannot complete.

### 5. Start the application

~~~bash
python run.py
~~~

Open <http://localhost:5000>. The health endpoint is available at <http://localhost:5000/health>.

The first face operation may take longer if the SFace model has not already been cached. Docker builds download and prepare the model during image creation instead.

---

## Run with Docker

### Build the image

~~~bash
docker build -t faceattend:latest .
~~~

### Run with persistent SQLite

The Dockerfile binds Gunicorn to the PORT environment variable. The example below uses port 10000, the same port exposed by the image, and persists both the database and logs on the host.

~~~bash
mkdir -p data logs

docker run -d \
  --name faceattend \
  --restart unless-stopped \
  --env-file .env \
  -e FLASK_ENV=production \
  -e PORT=10000 \
  -e DB_PATH=/app/data/attendance_system.db \
  -p 127.0.0.1:10000:10000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  faceattend:latest
~~~

On Windows PowerShell, replace the $(pwd) volume paths with absolute paths, for example D:\faceattend\data:/app/data.

Check the container:

~~~bash
docker ps
docker logs -f faceattend
~~~

### Run with PostgreSQL or RDS

Keep the persistent data volume for logs and emergency SQLite fallback, then provide DATABASE_URL in .env:

~~~dotenv
DATABASE_URL=postgresql://attendance_user:URL_ENCODED_PASSWORD@your-rds-endpoint:5432/faceattend
DB_PATH=/app/data/attendance_system.db
~~~

The application initializes the required tables in PostgreSQL on startup. Do not place a publicly reachable RDS endpoint or database credentials in source control.

### Why the default is one Gunicorn worker

The SFace model is memory-intensive compared with ordinary Flask routes, and APScheduler runs in the application process. Keep --workers 1 unless you deliberately redesign scheduler ownership and account for one face model per worker. Running the scheduler in multiple workers can duplicate scheduled jobs.

---

## Deploy to AWS EC2 with Amazon RDS

This is the recommended production-style deployment for a small or medium installation.

### Target layout

~~~text
Internet
   |
   v
HTTPS / 443
   |
EC2 security group
   |
Nginx :443  --->  Docker / Gunicorn :10000
                         |
                         +--> RDS PostgreSQL :5432
                         +--> EBS /app/data and /app/logs
                         +--> Gmail SMTP :587
~~~

### Step 1: Create the RDS database

Create an Amazon RDS for PostgreSQL instance in the same VPC as the EC2 host.

Recommended baseline:

- Keep the database **private**; do not allow public internet access unless there is a specific, reviewed requirement.
- Create a dedicated database and application user for FaceAttend.
- Enable automated backups and choose a retention window appropriate for the organization.
- Use the RDS endpoint, database name, username, and password to construct DATABASE_URL.
- Put the RDS instance and EC2 host in compatible subnets and availability zones for the required availability design.

### Step 2: Configure security groups

Use separate security groups:

| Resource | Inbound rule | Source |
| --- | --- | --- |
| EC2 | TCP 22 | Your fixed administrator IP only |
| EC2 | TCP 80 | Internet, if redirecting HTTP to HTTPS |
| EC2 | TCP 443 | Internet |
| RDS | TCP 5432 | **EC2 security group**, never 0.0.0.0/0 |

Do not expose the Gunicorn port directly to the public internet. Bind the container to 127.0.0.1:10000 and let Nginx handle public HTTP/S traffic.

### Step 3: Prepare EC2

Install Docker using the official Docker instructions for the EC2 operating system, then clone the repository into a controlled application directory. A typical layout is:

~~~text
/opt/faceattend/
├── app-source/       # cloned repository
├── data/             # persistent SQLite fallback, if enabled
├── logs/             # persistent application logs
└── .env              # server-only secrets, mode 600
~~~

Create .env with production values. A RDS-backed example is:

~~~dotenv
FLASK_ENV=production
SECRET_KEY=generate-a-long-random-secret
PORT=10000

DATABASE_URL=postgresql://attendance_user:URL_ENCODED_PASSWORD@your-rds-endpoint:5432/faceattend
DB_PATH=/app/data/attendance_system.db

SCHEDULER_ENABLED=true
FACE_RECOGNITION_THRESHOLD=12.0
SESSION_TIMEOUT_MINUTES=30

ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace-before-first-start
ADMIN_FULL_NAME=System Administrator

SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sender@gmail.com
SMTP_PASSWORD=GMAIL_APP_PASSWORD
SMTP_FROM=sender@gmail.com
SMTP_USE_TLS=true
SMTP_TIMEOUT_SECONDS=10

OTP_EXPIRES_MINUTES=10
OTP_MAX_ATTEMPTS=5
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_RESENDS=3
~~~

If the database password contains characters such as @, :, /, or #, URL-encode the password before putting it in the PostgreSQL connection string.

### Step 4: Build and start the container

~~~bash
cd /opt/faceattend/app-source
docker build -t faceattend:latest .

mkdir -p /opt/faceattend/data /opt/faceattend/logs

docker run -d \
  --name faceattend \
  --restart unless-stopped \
  --env-file /opt/faceattend/.env \
  -p 127.0.0.1:10000:10000 \
  -v /opt/faceattend/data:/app/data \
  -v /opt/faceattend/logs:/app/logs \
  faceattend:latest
~~~

Verify startup:

~~~bash
curl http://127.0.0.1:10000/health
docker logs --tail 200 faceattend
~~~

The health response should be:

~~~json
{"status":"ok"}
~~~

The startup logs should show successful database initialization. If RDS is unreachable, stop and correct the network or credentials issue before using the fallback database for production traffic.

### Step 5: Put Nginx in front of the container

Use a server block similar to this, replacing the hostname:

~~~nginx
server {
    listen 80;
    server_name attendance.example.com;

    location / {
        proxy_pass http://127.0.0.1:10000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
~~~

After DNS points to the EC2 public address, configure a trusted TLS certificate and redirect HTTP to HTTPS. Camera access normally requires a secure context; localhost is the main development exception.

### Step 6: Validate the end-to-end flow

1. Open the HTTPS hostname and confirm /health returns HTTP 200.
2. Sign in through /auth/admin-login with the bootstrapped administrator account.
3. Register a test employee and verify the Gmail OTP.
4. Sign in as the employee and register a face in good lighting.
5. Scan once during each required attendance band in a test environment.
6. Confirm the employee dashboard and administrator live roster show the same status.
7. Confirm an RDS snapshot or backup policy exists before real attendance data is collected.

### Production update flow

~~~bash
cd /opt/faceattend/app-source
git pull
docker build -t faceattend:latest .
docker rm -f faceattend
docker run -d \
  --name faceattend \
  --restart unless-stopped \
  --env-file /opt/faceattend/.env \
  -p 127.0.0.1:10000:10000 \
  -v /opt/faceattend/data:/app/data \
  -v /opt/faceattend/logs:/app/logs \
  faceattend:latest
~~~

Back up the database and review release changes before performing an upgrade. The docker rm -f command removes only the container; data remains in the mounted host directories and, in RDS mode, in RDS.

---

## Configuration reference

The safe starting point is .env.example. Copy it to .env, replace every placeholder, and keep .env out of Git.

### Application and session

| Variable | Default / example | Purpose |
| --- | --- | --- |
| FLASK_ENV | development | Controls production session-cookie security when set to production. |
| SECRET_KEY | change-this... in template | Flask session signing. Use a long, unpredictable secret in production. |
| SESSION_TIMEOUT_MINUTES | 30 | Permanent session lifetime configuration. |
| PORT | Set by deployment | Port consumed by the Docker/Gunicorn command. Local run.py uses port 5000. |

### Database

| Variable | Example | Purpose |
| --- | --- | --- |
| DATABASE_URL | postgresql://user:password@host:5432/database | Enables PostgreSQL, including Amazon RDS. postgres:// is also normalized to postgresql://. |
| DB_PATH | attendance_system.db or /app/data/attendance_system.db | SQLite path and fallback path when PostgreSQL is unavailable. |

When both variables are set, PostgreSQL is attempted first. Do not assume that setting both creates synchronization between the two databases.

### Administrator bootstrap

| Variable | Purpose |
| --- | --- |
| ADMIN_USERNAME | Initial administrator username |
| ADMIN_EMAIL | Initial administrator email |
| ADMIN_PASSWORD | Initial administrator password; always replace the template value |
| ADMIN_FULL_NAME | Initial administrator display name |

The administrator is created or ensured during startup. The password is stored as a hash in the database. Keep bootstrap credentials out of source control and rotate them through the application or a controlled database process after initial deployment.

### Face recognition

| Variable | Default | Purpose |
| --- | --- | --- |
| FACE_RECOGNITION_THRESHOLD | 12.0 | SFace raw Euclidean L2 distance threshold. Validate any change with real test images. |

### Scheduler

| Variable | Default | Purpose |
| --- | --- | --- |
| SCHEDULER_ENABLED | true | Enables the in-process APScheduler jobs. Set to false for local runs where automatic jobs are not wanted. |

The .env.example file also contains TIMEZONE, DEBUG, MAX_UPLOAD_SIZE, and LOG_LEVEL placeholders. These are not fully consumed by the current application code; the attendance business rules currently use IST and the scheduler timezone should be verified separately.

### Gmail SMTP and OTP

| Variable | Example | Purpose |
| --- | --- | --- |
| SMTP_ENABLED | true | Enables Gmail SMTP delivery. |
| SMTP_HOST | smtp.gmail.com | SMTP server hostname. |
| SMTP_PORT | 587 | SMTP port. |
| SMTP_USERNAME | sender@gmail.com | Gmail sender account. |
| SMTP_PASSWORD | App Password | Google App Password, not the normal Gmail password. |
| SMTP_FROM | sender@gmail.com | From address or authorized alias. |
| SMTP_USE_TLS | true | Uses STARTTLS. |
| SMTP_TIMEOUT_SECONDS | 10 | SMTP network timeout. |
| OTP_EXPIRES_MINUTES | 10 | OTP validity period. |
| OTP_MAX_ATTEMPTS | 5 | Invalid-code attempt limit. |
| OTP_RESEND_COOLDOWN_SECONDS | 60 | Minimum delay between resends. |
| OTP_MAX_RESENDS | 3 | Maximum resend count for a pending flow. |

To use Gmail SMTP, enable 2-Step Verification, create a Google App Password, and use that generated value as SMTP_PASSWORD. Never log or commit the value.

---

## Routes and API

### Browser routes

| Method | Path | Access | Description |
| --- | --- | --- | --- |
| GET | /health | Public | Lightweight process health response |
| GET | /auth/login | Public | Employee login |
| GET | /auth/admin-login | Public | Administrator login |
| GET/POST | /auth/register | Public | Start Gmail-verified employee registration |
| GET/POST | /auth/verify-email | Public | Verify the six-digit registration OTP |
| GET/POST | /auth/forgot-password | Employee | Start password recovery |
| GET/POST | /auth/verify-reset-otp | Employee | Verify the four-digit recovery OTP |
| GET/POST | /auth/reset-password | Employee | Choose a new password or keep the current one |
| GET | /dashboard | Employee | Employee dashboard |
| GET | /camera | Employee | Camera attendance terminal |
| GET | /report | Authenticated user | Attendance reporting view |
| GET | /admin | Administrator | Live administrator dashboard |
| GET | /admin/users | Administrator | Employee management |

### JSON API

| Method | Path | Authentication | Description |
| --- | --- | --- | --- |
| POST | /api/register-user | Employee session | Create or force-update the current user's face embedding |
| POST | /api/recognize-face | Public endpoint | Generate an embedding, identify a user, and attempt to mark attendance |
| GET | /api/attendance | Employee session | Paginated history with canonical status values |
| GET | /api/users | Public endpoint | Return basic user IDs and display names |
| GET | /api/admin/attendance/today | Administrator session | Live roster for active, non-admin employees |
| GET | /api/admin/attendance/history/<user_id> | Administrator session | Paginated individual employee history |

The face endpoints accept JSON with an image property containing a browser camera image, commonly a base64 data URL:

~~~json
{
  "image": "data:image/jpeg;base64,..."
}
~~~

An attendance recognition response includes the matched employee, status, timestamp, and a message. Common non-error status values include present, late, half_day, duplicate, already_absent, office_closed, and office_closed_sunday.

The employee history endpoint supports start_date, end_date, status, page, and page_size query parameters. Dates use YYYY-MM-DD.

---

## Database schema

The application creates these tables automatically in SQLite or PostgreSQL:

| Table | Role |
| --- | --- |
| users | Employee and administrator identities, password hashes, profile picture reference, role, status, verification state, and face embedding |
| attendance | One daily record per user, including time in/out, status, notes, and marker |
| working_hours | Weekday schedule defaults |
| attendance_reports | Daily, weekly, or monthly report records |
| email_notifications | Notification status records |
| audit_logs | Security and attendance audit events |
| pending_email_verifications | Hashed registration OTPs and registration data before account creation |
| password_reset_otps | Hashed employee recovery OTPs and attempt/resend state |

Embeddings are stored as serialized vectors in the users.embedding field. Captured recognition frames are processed in memory by the API and are not intended to be stored as attendance photos. Profile pictures are a separate account feature and should be governed by the same privacy policy.

---

## Operations and maintenance

### Scheduled jobs

When SCHEDULER_ENABLED=true, the application starts an APScheduler background scheduler with these jobs:

| Job | Declared schedule | Function |
| --- | --- | --- |
| End-of-day absent marking | 17:00, Monday–Saturday | Creates absent rows for enrolled employees without attendance |
| Daily summaries | 17:15, Monday–Saturday | Invokes the daily summary notification hook |
| Monthly reports | First day of the month at 23:00 | Generates monthly summaries and audit entries |

The scheduler is in-process. Run one application worker or move scheduling to a dedicated worker before scaling the web process horizontally.

### Logs

The application creates rotating logs under logs/:

- application.log — general application events
- attendance.log — attendance-specific events
- auth.log — authentication events
- errors.log — error-level events

In Docker, mount /app/logs to persistent host storage or forward container logs to your centralized logging platform. Never log passwords, OTP values, SMTP secrets, or raw biometric images.

### Backups

For SQLite:

- Stop the application before copying the database file, or use a SQLite-aware backup process.
- Back up the database and /app/data to encrypted, access-controlled storage.
- Test restoration periodically.

For RDS:

- Use automated backups and snapshots.
- Restrict database permissions to the application user and approved operators.
- Test restoring a snapshot into a non-production instance.
- Monitor storage, CPU, memory, connections, and failed connection attempts.

### Clearing attendance data

clear_attendance.py deletes every row from the attendance table after administrator authentication and a YES confirmation. It does not delete users or face embeddings.

Run it only after taking a backup and preferably while the application is stopped:

~~~bash
python clear_attendance.py
~~~

This is a destructive operation and cannot be undone by the script.

---

## Security and privacy checklist

Before exposing the application to real users:

- Replace the development SECRET_KEY and default admin credentials.
- Store .env outside Git with restrictive permissions such as chmod 600 .env.
- Use HTTPS for every non-local deployment, especially camera pages.
- Keep RDS private and allow PostgreSQL only from the EC2 security group.
- Use a Gmail App Password or an approved SMTP provider credential; never use a normal mailbox password.
- Rotate secrets through the deployment environment, not by committing them to the repository.
- Restrict administrator access and review administrator audit events.
- Define consent, retention, deletion, access, and incident-response policies for biometric data.
- Configure encrypted storage and backups for embeddings, attendance, and logs.
- Validate recognition thresholds and add a human override process for false matches or missed scans.
- Add liveness or anti-spoofing controls before treating recognition as a high-assurance identity factor.

The current project is an application foundation, not a complete compliance package or certified biometric security system. Review the password-hashing, session, CSRF, rate-limiting, retention, and privacy requirements for the intended environment before production launch.

---

## Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| 502 Bad Gateway from Nginx | Container is stopped or bound to the wrong port | Check docker ps, docker logs faceattend, PORT=10000, and the 127.0.0.1:10000 mapping |
| Camera does not open | Browser permission denied or page is not HTTPS | Allow camera permission and use HTTPS outside localhost |
| Face is enrolled but not recognized | Lighting, pose, stale embedding, or threshold mismatch | Improve lighting, re-register, and start with FACE_RECOGNITION_THRESHOLD=12.0 |
| Registration email never arrives | SMTP disabled, invalid App Password, spam filtering, or provider quota | Check SMTP variables and application logs; never expose the credential |
| RDS connection fails | Security group, subnet, endpoint, password, or URL-encoding issue | Test from EC2, allow 5432 from the EC2 security group, and inspect startup logs |
| Data appears in the wrong database | RDS failed and the automatic SQLite fallback activated | Restore RDS connectivity, inspect /app/data, and reconcile any fallback writes manually |
| Users are marked absent at the wrong time | Host/container timezone differs from the intended IST schedule | Verify the process timezone and scheduler configuration before enabling automatic jobs |
| Employee and admin statuses differ | Stale browser data or an older deployment | Refresh both clients and confirm both views use the current shared status logic |

---

## Limitations and roadmap

Current limitations and sensible next steps include:

- Liveness detection and stronger anti-spoofing
- Versioned database migrations
- A dedicated scheduler/worker for multi-instance deployments
- Organization, tenant, and configurable shift support
- Richer export and analytics capabilities
- Per-user password salts and a modern password-hashing library migration plan
- Centralized secret management and observability integrations
- Formal biometric retention and deletion workflows

---

## License and credits

This repository does not currently declare a formal open-source license. Confirm licensing terms before redistributing or operating it commercially.

Built with:

- [Flask](https://flask.palletsprojects.com/)
- [DeepFace](https://github.com/serengil/deepface)
- [SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface)
- [APScheduler](https://apscheduler.readthedocs.io/)
- [PostgreSQL](https://www.postgresql.org/)
- [SQLite](https://www.sqlite.org/)

---

<div align="center">

**FaceAttend** · clear attendance records, camera-based recognition, and deployment flexibility from SQLite to AWS.

</div>
