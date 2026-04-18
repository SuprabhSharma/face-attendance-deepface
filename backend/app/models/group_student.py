"""GroupStudent model — junction table linking students to groups."""

from app.extensions import db


class GroupStudent(db.Model):
    __tablename__ = "group_students"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer, db.ForeignKey("groups.id"), nullable=False, index=True
    )
    student_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    # Prevent duplicate enrolments
    __table_args__ = (
        db.UniqueConstraint("group_id", "student_id", name="uq_group_student"),
    )

    student = db.relationship("User", backref="group_memberships")

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "student_email": self.student.email if self.student else None,
        }
