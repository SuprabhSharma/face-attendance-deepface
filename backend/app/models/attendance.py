"""Attendance model — individual student attendance records."""

from datetime import datetime, timezone
from app.extensions import db


class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("attendance_sessions.id"),
        nullable=True,
        index=True,
    )
    group_id = db.Column(
        db.Integer, db.ForeignKey("groups.id"), nullable=False, index=True
    )
    student_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    status = db.Column(db.String(10), nullable=False)  # 'present' or 'absent'
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "group_id": self.group_id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
