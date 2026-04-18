"""User model — trainers and students."""

from datetime import datetime, timezone
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'trainer' or 'student'
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    groups = db.relationship(
        "Group", backref="trainer", lazy="dynamic", foreign_keys="Group.trainer_id"
    )
    face_data = db.relationship("FaceData", backref="user", lazy="dynamic")
    attendances = db.relationship("Attendance", backref="student", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
