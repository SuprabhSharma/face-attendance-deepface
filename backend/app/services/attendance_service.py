"""Attendance service — sessions, marking, and history."""

from datetime import datetime, timezone

from app.extensions import db
from app.models.attendance import Attendance
from app.models.attendance_session import AttendanceSession
from app.models.group import Group
from app.models.group_student import GroupStudent


def start_session(group_id: int, trainer_id: int):
    """Create a new attendance session for a group."""
    group = Group.query.get(group_id)
    if not group:
        return {"success": False, "message": "Group not found."}, 404
    if group.trainer_id != trainer_id:
        return {"success": False, "message": "Not authorised."}, 403

    # Check for an already-open session
    open_session = AttendanceSession.query.filter_by(
        group_id=group_id, ended_at=None
    ).first()
    if open_session:
        return {
            "success": True,
            "message": "Session already active.",
            "session": open_session.to_dict(),
        }, 200

    session = AttendanceSession(group_id=group_id)
    db.session.add(session)
    db.session.commit()

    return {
        "success": True,
        "message": "Attendance session started.",
        "session": session.to_dict(),
    }, 201


def end_session(session_id: int, trainer_id: int):
    """End an attendance session and auto-mark absent students."""
    session = AttendanceSession.query.get(session_id)
    if not session:
        return {"success": False, "message": "Session not found."}, 404

    group = Group.query.get(session.group_id)
    if not group or group.trainer_id != trainer_id:
        return {"success": False, "message": "Not authorised."}, 403

    if session.ended_at:
        return {"success": False, "message": "Session already ended."}, 400

    # Auto-mark absent: find students who were NOT marked present
    all_student_ids = {
        gs.student_id
        for gs in GroupStudent.query.filter_by(group_id=session.group_id).all()
    }
    present_ids = {
        a.student_id
        for a in Attendance.query.filter_by(
            session_id=session.id, status="present"
        ).all()
    }
    absent_ids = all_student_ids - present_ids

    now = datetime.now(timezone.utc)
    for sid in absent_ids:
        att = Attendance(
            session_id=session.id,
            group_id=session.group_id,
            student_id=sid,
            status="absent",
            timestamp=now,
        )
        db.session.add(att)

    session.ended_at = now
    db.session.commit()

    return {
        "success": True,
        "message": f"Session ended. {len(absent_ids)} student(s) marked absent.",
        "session": session.to_dict(),
    }, 200


def mark_present(session_id: int, student_id: int, group_id: int):
    """Mark a single student as present in the given session."""
    # Prevent duplicate marking
    existing = Attendance.query.filter_by(
        session_id=session_id, student_id=student_id
    ).first()
    if existing:
        return {
            "success": True,
            "message": "Already marked.",
            "already_marked": True,
        }, 200

    att = Attendance(
        session_id=session_id,
        group_id=group_id,
        student_id=student_id,
        status="present",
    )
    db.session.add(att)
    db.session.commit()

    return {
        "success": True,
        "message": "Marked present.",
        "attendance": att.to_dict(),
    }, 201


def get_student_attendance(student_id: int):
    """Return full attendance history for a student with stats."""
    records = (
        Attendance.query.filter_by(student_id=student_id)
        .order_by(Attendance.timestamp.desc())
        .all()
    )

    total = len(records)
    present = sum(1 for r in records if r.status == "present")
    absent = total - present

    return {
        "success": True,
        "stats": {"total": total, "present": present, "absent": absent},
        "records": [r.to_dict() for r in records],
    }, 200


def get_session_attendance(session_id: int):
    """Return all attendance records for a given session."""
    records = Attendance.query.filter_by(session_id=session_id).all()
    return {
        "success": True,
        "records": [r.to_dict() for r in records],
    }, 200


def get_group_attendance(group_id: int):
    """Return all attendance records for a group (across all sessions)."""
    records = (
        Attendance.query.filter_by(group_id=group_id)
        .order_by(Attendance.timestamp.desc())
        .all()
    )
    return {
        "success": True,
        "records": [r.to_dict() for r in records],
    }, 200
