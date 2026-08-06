"""Face embedding and matching helpers used by registration and attendance."""

import json
import logging
import os

import numpy as np
from deepface import DeepFace

from app.models.db import get_all_users

logger = logging.getLogger(__name__)

MODEL_NAME = "Facenet"
DEFAULT_MATCH_THRESHOLD = 0.80


def get_match_threshold():
    """Get the L2 threshold for normalized FaceNet embeddings."""
    raw_value = os.getenv("FACE_RECOGNITION_THRESHOLD", str(DEFAULT_MATCH_THRESHOLD))
    try:
        threshold = float(raw_value)
    except (TypeError, ValueError):
        logger.warning("Invalid FACE_RECOGNITION_THRESHOLD; using %.2f", DEFAULT_MATCH_THRESHOLD)
        return DEFAULT_MATCH_THRESHOLD

    if not 0 < threshold <= 2:
        logger.warning("FACE_RECOGNITION_THRESHOLD must be between 0 and 2; using %.2f", DEFAULT_MATCH_THRESHOLD)
        return DEFAULT_MATCH_THRESHOLD

    return threshold


def get_face_embedding(image):
    """Create one normalized FaceNet embedding from an image containing one face."""
    try:
        if image is None:
            return None, "Image not loaded"

        result = DeepFace.represent(
            img_path=image,
            model_name=MODEL_NAME,
            enforce_detection=True,
            detector_backend="opencv",
        )
        if isinstance(result, dict):
            result = [result]

        if not result:
            return None, "No face detected. Look directly at the camera and try again."
        if len(result) != 1:
            return None, "Exactly one face must be visible."

        embedding = np.asarray(result[0]["embedding"], dtype=np.float32)
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return None, "Invalid face embedding"

        return embedding / norm, None
    except Exception as error:
        logger.exception("Could not create face embedding")
        return None, "Could not process this face. Ensure good lighting and try again."


def recognize_user(embedding, threshold=None, exclude_user_id=None):
    """Return the closest enrolled user when it is within the match threshold."""
    if embedding is None:
        return None, None

    threshold = get_match_threshold() if threshold is None else threshold
    best_match = None
    best_distance = float("inf")

    try:
        for user in get_all_users():
            if user.get("id") == exclude_user_id or not user.get("embedding"):
                continue

            try:
                stored = np.asarray(json.loads(user["embedding"]), dtype=np.float32)
                norm = np.linalg.norm(stored)
                if norm == 0:
                    continue
                stored = stored / norm
            except (TypeError, ValueError, json.JSONDecodeError):
                logger.warning("Skipping invalid face embedding for user_id=%s", user.get("id"))
                continue

            distance = float(np.linalg.norm(stored - embedding))
            logger.info("Face comparison user_id=%s distance=%.4f threshold=%.4f", user["id"], distance, threshold)
            if distance < best_distance:
                best_distance = distance
                best_match = user

        if best_match and best_distance <= threshold:
            logger.info("Face matched user_id=%s distance=%.4f", best_match["id"], best_distance)
            return best_match["id"], best_match.get("full_name") or best_match.get("username")

        logger.info("Face not matched; nearest_distance=%.4f threshold=%.4f", best_distance, threshold)
        return None, None
    except Exception:
        logger.exception("Face recognition failed")
        return None, None


def check_duplicate_face(embedding, threshold=None, exclude_user_id=None):
    user_id, name = recognize_user(embedding, threshold, exclude_user_id)
    return (user_id is not None), name
