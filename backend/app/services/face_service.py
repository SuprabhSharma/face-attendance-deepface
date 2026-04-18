"""Face recognition service — encoding, storage, and matching."""

import pickle

import cv2
import face_recognition
import numpy as np

from app.extensions import db
from app.models.face_data import FaceData
from app.models.group_student import GroupStudent


def get_face_embedding(img):
    """Extract a 128-d face encoding from a BGR OpenCV image.

    Returns ``(numpy_array, None)`` on success or ``(None, error_string)`` on failure.
    """
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(img_rgb)

    if len(face_locations) == 0:
        return None, "No face detected. Please look directly at the camera."

    if len(face_locations) > 1:
        return None, "Multiple faces detected. Please ensure only one person is in frame."

    embedding = face_recognition.face_encodings(img_rgb, face_locations)[0]
    return embedding, None


def get_multiple_face_embeddings(img):
    """Extract ALL face encodings from a BGR image (for batch attendance scanning).

    Returns ``(list_of_numpy_arrays, face_locations, None)`` or ``(None, None, error)``.
    """
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Downscale for speed
    small = cv2.resize(img_rgb, (0, 0), fx=0.5, fy=0.5)
    face_locations = face_recognition.face_locations(small)

    if len(face_locations) == 0:
        return None, None, "No faces detected in frame."

    embeddings = face_recognition.face_encodings(small, face_locations)
    return embeddings, face_locations, None


def store_face_encoding(user_id: int, embedding: np.ndarray):
    """Persist a face encoding as pickled BYTEA."""
    blob = pickle.dumps(embedding)
    fd = FaceData(user_id=user_id, encoding=blob)
    db.session.add(fd)
    db.session.commit()
    return fd.id


def check_duplicate_face(embedding: np.ndarray, tolerance: float = 0.5):
    """Check whether this face already exists in the database.

    Returns ``(True, user_name)`` if duplicate, else ``(False, None)``.
    """
    all_face_data = FaceData.query.all()
    if not all_face_data:
        return False, None

    known_encodings = []
    user_ids = []
    for fd in all_face_data:
        known_encodings.append(pickle.loads(fd.encoding))
        user_ids.append(fd.user_id)

    matches = face_recognition.compare_faces(known_encodings, embedding, tolerance=tolerance)
    distances = face_recognition.face_distance(known_encodings, embedding)

    if len(distances) > 0:
        best_idx = np.argmin(distances)
        if matches[best_idx]:
            from app.models.user import User

            user = User.query.get(user_ids[best_idx])
            return True, user.name if user else "Unknown"

    return False, None


def recognize_faces_in_group(embedding: np.ndarray, group_id: int, tolerance: float = 0.5):
    """Match a single embedding against all students in a given group.

    Returns ``(user_id, user_name)`` or ``(None, None)``.
    """
    student_ids = [
        gs.student_id
        for gs in GroupStudent.query.filter_by(group_id=group_id).all()
    ]
    if not student_ids:
        return None, None

    face_rows = FaceData.query.filter(FaceData.user_id.in_(student_ids)).all()
    if not face_rows:
        return None, None

    known_encodings = []
    known_user_ids = []
    for fd in face_rows:
        known_encodings.append(pickle.loads(fd.encoding))
        known_user_ids.append(fd.user_id)

    matches = face_recognition.compare_faces(known_encodings, embedding, tolerance=tolerance)
    distances = face_recognition.face_distance(known_encodings, embedding)

    if len(distances) > 0:
        best_idx = np.argmin(distances)
        if matches[best_idx]:
            from app.models.user import User

            user = User.query.get(known_user_ids[best_idx])
            return user.id if user else None, user.name if user else None

    return None, None
