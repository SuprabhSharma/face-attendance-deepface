"""Face embedding and matching helpers — uses SFace (28MB, lightweight, fast)."""

import json
import logging
import os

import numpy as np
from deepface import DeepFace

from app.models.db import get_all_users

# Suppress noisy TensorFlow / TF-TRT logs
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# MODEL CONFIG
# SFace: 28MB, edge-optimised, raw L2 threshold ~10-13
# ─────────────────────────────────────────────
MODEL_NAME = "SFace"
DEFAULT_MATCH_THRESHOLD = 12.0   # raw L2 distance — SFace same-person ≈ 0-10, different ≈ 13+
DETECTOR_BACKEND = "opencv"      # fastest detector

# Preload SFace model on module load to prevent cold-start API timeouts
try:
    logger.info("Preloading SFace model into memory...")
    DeepFace.build_model(MODEL_NAME)
    logger.info("SFace model preloaded successfully.")
except Exception as _preload_err:
    logger.warning("Could not preload SFace model: %s", _preload_err)


def get_match_threshold():
    """Read threshold from env (FACE_RECOGNITION_THRESHOLD) with safe fallback."""
    raw = os.getenv("FACE_RECOGNITION_THRESHOLD", str(DEFAULT_MATCH_THRESHOLD))
    try:
        val = float(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid FACE_RECOGNITION_THRESHOLD '%s'; using %.1f", raw, DEFAULT_MATCH_THRESHOLD)
        return DEFAULT_MATCH_THRESHOLD

    if val <= 0 or val > 50:
        logger.warning("FACE_RECOGNITION_THRESHOLD=%.1f out of range; using %.1f", val, DEFAULT_MATCH_THRESHOLD)
        return DEFAULT_MATCH_THRESHOLD

    return val


def _get_face_area(face_dict):
    """Calculate bounding box area (w * h) for a face dictionary from DeepFace."""
    region = face_dict.get("facial_area") or {}
    w = region.get("w", 0)
    h = region.get("h", 0)
    return w * h


def get_face_embedding(image):
    """
    Generate one SFace embedding from a cv2 image (BGR numpy array).
    Selects the largest/primary face if background noise occurs.
    Returns (embedding_ndarray, None) on success, or (None, error_str) on failure.
    """
    if image is None:
        return None, "Image not loaded."

    try:
        result = DeepFace.represent(
            img_path=image,
            model_name=MODEL_NAME,
            enforce_detection=False,
            detector_backend=DETECTOR_BACKEND,
        )

        if isinstance(result, dict):
            result = [result]

        if not result:
            return None, "No face detected. Look directly at the camera in good lighting."

        valid_results = [r for r in result if r.get("embedding") is not None]

        if not valid_results:
            return None, "Could not extract face features. Please adjust lighting and try again."

        if len(valid_results) > 1:
            valid_results.sort(key=_get_face_area, reverse=True)
            logger.info("Multiple face candidates detected (%d). Selected primary face by size.", len(valid_results))

        primary_face = valid_results[0]
        embedding = np.asarray(primary_face["embedding"], dtype=np.float32)

        if embedding.size == 0:
            return None, "Empty face embedding — please try again."

        return embedding, None

    except Exception:
        logger.exception("get_face_embedding failed")
        return None, "Could not process face. Ensure good lighting and look directly at the camera."


def recognize_user(embedding, threshold=None, exclude_user_id=None):
    """
    Return (user_id, display_name) of the best matching enrolled user,
    or (None, None) if no match is found within the threshold.
    """
    if embedding is None:
        return None, None

    threshold = get_match_threshold() if threshold is None else threshold
    best_match = None
    best_distance = float("inf")

    try:
        for user in get_all_users():
            if exclude_user_id is not None and user.get("id") == exclude_user_id:
                continue
            if not user.get("embedding"):
                continue

            try:
                stored = np.asarray(json.loads(user["embedding"]), dtype=np.float32)
            except (TypeError, ValueError, json.JSONDecodeError):
                logger.warning("Skipping corrupt embedding for user_id=%s", user.get("id"))
                continue

            if stored.size == 0:
                continue

            distance = float(np.linalg.norm(stored - embedding))
            logger.info(
                "SFace comparison user_id=%s distance=%.2f threshold=%.1f",
                user["id"], distance, threshold,
            )

            if distance < best_distance:
                best_distance = distance
                best_match = user

        if best_match and best_distance <= threshold:
            logger.info("Face MATCHED user_id=%s distance=%.2f", best_match["id"], best_distance)
            return best_match["id"], best_match.get("full_name") or best_match.get("username")

        logger.info("Face NOT matched — best_distance=%.2f threshold=%.1f", best_distance, threshold)
        return None, None

    except Exception:
        logger.exception("recognize_user failed")
        return None, None


def check_duplicate_face(embedding, threshold=None, exclude_user_id=None):
    """Return (True, user_id, name) if this face matches an enrolled user."""
    matched_user_id, name = recognize_user(embedding, threshold, exclude_user_id)
    if matched_user_id is not None:
        return True, matched_user_id, name
    return False, None, None
