# 📄 Software Requirements Specification (SRS)

## 🎯 Project Title

**Face Recognition Based Attendance System**

---

## 1. 📌 Introduction

### 1.1 Purpose

This system automates attendance tracking using facial recognition. It allows trainers to manage student groups and record attendance, while students can view their attendance records.

### 1.2 Scope

The system will:

* Authenticate users (Trainer / Student)
* Allow trainers to manage groups and students
* Capture attendance using face recognition
* Store timestamped attendance records
* Provide dashboards for both roles

---

## 2. 👥 User Roles

### 2.1 Trainer

* Register / Login
* Create and manage groups
* Add/remove students
* Capture attendance via face recognition
* View attendance reports

### 2.2 Student

* Register / Login
* View personal attendance history

---

## 3. ⚙️ Functional Requirements

### 3.1 Authentication

* Users can sign up with:

  * Name
  * Email
  * Password
  * Role (Trainer / Student)

* Secure login system (JWT-based recommended)

---

### 3.2 Group Management (Trainer)

* Create group
* Add students via email
* Remove students
* Update group details

---

### 3.3 Face Registration

* Students upload face data (images or embeddings)
* System stores face encodings

---

### 3.4 Attendance System

* Trainer starts attendance session

* System uses webcam to:

  * Detect faces
  * Match with stored encodings

* Mark:

  * Present (recognized faces)
  * Absent (remaining students)

* Store:

  * Date
  * Time
  * Student ID
  * Status

---

### 3.5 Dashboard

#### Trainer Dashboard

* Create / manage groups
* Start attendance
* View reports

#### Student Dashboard

* View attendance records
* See present/absent stats

---

## 4. 🚫 Non-Functional Requirements

* **Performance:** Real-time face recognition (within 1–2 sec per frame)
* **Security:** Password hashing (bcrypt), JWT auth
* **Scalability:** Modular backend (Flask APIs)
* **Usability:** Simple UI (React)
* **Reliability:** Accurate face recognition

---

## 5. 🧱 System Architecture

* **Frontend:** React.js
* **Backend:** Flask (Python)
* **Face Recognition:**

  * `face_recognition` library / OpenCV
* **Database:** PostgreSQL

---

## 6. 🗄️ Database Design

### 6.1 Users Table

```
users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(100) UNIQUE,
  password TEXT,
  role VARCHAR(10), -- trainer / student
  created_at TIMESTAMP
)
```

---

### 6.2 Groups Table

```
groups (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  trainer_id INTEGER REFERENCES users(id),
  created_at TIMESTAMP
)
```

---

### 6.3 Group_Students Table

```
group_students (
  id SERIAL PRIMARY KEY,
  group_id INTEGER REFERENCES groups(id),
  student_id INTEGER REFERENCES users(id)
)
```

---

### 6.4 Face_Data Table

```
face_data (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  encoding BYTEA, -- serialized face encoding
  created_at TIMESTAMP
)
```

---

### 6.5 Attendance Table

```
attendance (
  id SERIAL PRIMARY KEY,
  group_id INTEGER REFERENCES groups(id),
  student_id INTEGER REFERENCES users(id),
  status VARCHAR(10), -- present / absent
  timestamp TIMESTAMP
)
```

---

### 6.6 Attendance_Sessions Table (optional but good)

```
attendance_sessions (
  id SERIAL PRIMARY KEY,
  group_id INTEGER,
  started_at TIMESTAMP
)
```

---

## 7. 🔌 API Endpoints (High-Level)

### Auth

* POST `/register`
* POST `/login`

### Groups

* POST `/groups`
* GET `/groups`
* PUT `/groups/:id`
* DELETE `/groups/:id`

### Students

* POST `/groups/:id/add-student`
* DELETE `/groups/:id/remove-student`

### Face Recognition

* POST `/upload-face`
* POST `/recognize-face`

### Attendance

* POST `/attendance/start`
* POST `/attendance/mark`
* GET `/attendance/:studentId`

---

## 8. 🖥️ Frontend Modules (React)

* Auth (Login / Signup)
* Trainer Dashboard

  * Group Management
  * Attendance Screen (camera UI)
* Student Dashboard

  * Attendance history

---

## 9. 🔥 Key Challenges (Important for Interview)

* Face encoding storage & matching
* Real-time recognition performance
* Handling false positives
* Clean role-based access control

---

## 10. 🚀 Future Enhancements

* Attendance analytics (graphs)
* Mobile support
* Live classroom monitoring
* Multi-face detection optimization
