"""FaceData model — stores serialised face encodings (BYTEA)."""

from datetime import datetime, timezone
from app.extensions import db


class FaceData(db.Model):
    __tablename__ = "face_data"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    encoding = db.Column(db.LargeBinary, nullable=False)  # pickled numpy array
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
