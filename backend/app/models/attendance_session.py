"""AttendanceSession model — tracks when a trainer starts attendance."""

from datetime import datetime, timezone
from app.extensions import db


class AttendanceSession(db.Model):
    __tablename__ = "attendance_sessions"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer, db.ForeignKey("groups.id"), nullable=False, index=True
    )
    started_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    ended_at = db.Column(db.DateTime, nullable=True)

    attendances = db.relationship(
        "Attendance", backref="session", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }
