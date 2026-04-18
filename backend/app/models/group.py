"""Group model — created by trainers to organise students."""

from datetime import datetime, timezone
from app.extensions import db


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    trainer_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    students = db.relationship(
        "GroupStudent", backref="group", lazy="dynamic", cascade="all, delete-orphan"
    )
    sessions = db.relationship(
        "AttendanceSession", backref="group", lazy="dynamic", cascade="all, delete-orphan"
    )
    attendances = db.relationship(
        "Attendance", backref="group", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "trainer_id": self.trainer_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "student_count": self.students.count(),
        }
