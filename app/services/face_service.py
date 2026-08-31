"""Face embedding and matching helpers — uses SFace (28MB, lightweight, fast)."""

import json
import logging
import os

import cv2
import numpy as np
from deepface import DeepFace

from app.models.db import get_all_users, is_face_enrolled

# Suppress noisy TensorFlow / TF-TRT logs
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# MODEL CONFIG
# SFace: 28MB, edge-optimised, raw L2 threshold ~10-13
# Same person typically L2 ≈ 0–10; different people ≈ 13+
# ─────────────────────────────────────────────
MODEL_NAME = "SFace"
DEFAULT_MATCH_THRESHOLD = 12.0   # raw Euclidean L2 distance
DETECTOR_BACKEND = "opencv"      # fastest detector
MIN_FACE_AREA = 40 * 40          # reject tiny/false detections


def get_match_threshold():
    """Read FACE_RECOGNITION_THRESHOLD as SFace L2 distance.

    Values like 0.80 are cosine-style and will reject every real match.
    Those are auto-corrected to the SFace default (12.0).
    """
    raw = os.getenv("FACE_RECOGNITION_THRESHOLD", str(DEFAULT_MATCH_THRESHOLD))
    try:
        val = float(raw)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid FACE_RECOGNITION_THRESHOLD %r; using %.1f",
            raw, DEFAULT_MATCH_THRESHOLD,
        )
        return DEFAULT_MATCH_THRESHOLD

    # Cosine/similarity style configs are typically 0–1 (sometimes up to ~2)
    if val < 2.0:
        logger.warning(
            "FACE_RECOGNITION_THRESHOLD=%.3f looks like a cosine threshold; "
            "SFace uses L2 distance. Using default %.1f instead.",
            val, DEFAULT_MATCH_THRESHOLD,
        )
        return DEFAULT_MATCH_THRESHOLD

    if val > 50:
        logger.warning(
            "FACE_RECOGNITION_THRESHOLD=%.1f out of range; using %.1f",
            val, DEFAULT_MATCH_THRESHOLD,
        )
        return DEFAULT_MATCH_THRESHOLD

    return val


def _get_face_area(face_dict):
    """Bounding-box area (w * h) for a DeepFace face dict."""
    region = face_dict.get("facial_area") or {}
    w = region.get("w", 0) or 0
    h = region.get("h", 0) or 0
    return w * h


# Preload SFace model on module load to prevent cold-start API timeouts
try:
    logger.info("Preloading SFace model into memory...")
    DeepFace.build_model(MODEL_NAME)
    logger.info("SFace model preloaded successfully.")
except Exception as _preload_err:
    logger.warning("Could not preload SFace model: %s", _preload_err)


def get_face_embedding(image):
    """
    Generate one SFace embedding from a cv2 image (BGR numpy array).
    Selects the largest primary face if multiple are present.
    Returns (embedding_ndarray, None) on success, or (None, error_str) on failure.
    """
    if image is None:
        return None, "Image not loaded."

    try:
        # Downscale large frames for speed (keep aspect)
        h, w = image.shape[:2]
        if w > 640:
            scale = 640.0 / w
            image = cv2.resize(image, (640, max(1, int(h * scale))))

        result = DeepFace.represent(
            img_path=image,
            model_name=MODEL_NAME,
            enforce_detection=True,
            detector_backend=DETECTOR_BACKEND,
        )

        if isinstance(result, dict):
            result = [result]

        if not result:
            return None, "No face detected. Look directly at the camera in good lighting."

        valid_results = [
            r for r in result
            if r.get("embedding") is not None and _get_face_area(r) >= MIN_FACE_AREA
        ]

        if not valid_results:
            # Fall back to any embedding if area metadata is missing
            valid_results = [r for r in result if r.get("embedding") is not None]

        if not valid_results:
            return None, "Could not extract face features. Please adjust lighting and try again."

        if len(valid_results) > 1:
            valid_results.sort(key=_get_face_area, reverse=True)
            logger.info(
                "Multiple face candidates detected (%d). Selected primary face by size.",
                len(valid_results),
            )

        primary_face = valid_results[0]
        embedding = np.asarray(primary_face["embedding"], dtype=np.float32).reshape(-1)

        if embedding.size == 0:
            return None, "Empty face embedding — please try again."

        return embedding, None

    except ValueError as ve:
        # DeepFace raises ValueError when enforce_detection=True and no face found
        logger.info("Face detection failed: %s", ve)
        return None, "No face detected. Look directly at the camera in good lighting."
    except Exception:
        logger.exception("get_face_embedding failed")
        return None, "Could not process face. Ensure good lighting and look directly at the camera."


def _load_stored_embedding(raw):
    """Parse stored JSON embedding. Returns ndarray or None."""
    if not is_face_enrolled(raw):
        return None
    try:
        if isinstance(raw, (list, tuple)):
            stored = np.asarray(raw, dtype=np.float32).reshape(-1)
        else:
            stored = np.asarray(json.loads(raw), dtype=np.float32).reshape(-1)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if stored.size == 0:
        return None
    return stored


def recognize_user(embedding, threshold=None, exclude_user_id=None):
    """
    Return (user_id, display_name) of the best matching enrolled user,
    or (None, None) if no match is found within the threshold.
    """
    if embedding is None:
        return None, None

    threshold = get_match_threshold() if threshold is None else threshold
    query = np.asarray(embedding, dtype=np.float32).reshape(-1)

    best_match = None
    best_distance = float("inf")
    compared = 0

    try:
        for user in get_all_users():
            if exclude_user_id is not None and user.get("id") == exclude_user_id:
                continue

            stored = _load_stored_embedding(user.get("embedding"))
            if stored is None:
                continue

            if stored.size != query.size:
                logger.warning(
                    "Skipping user_id=%s — embedding dim %s != query dim %s",
                    user.get("id"), stored.size, query.size,
                )
                continue

            distance = float(np.linalg.norm(stored - query))
            compared += 1
            logger.info(
                "SFace comparison user_id=%s distance=%.3f threshold=%.1f",
                user["id"], distance, threshold,
            )

            if distance < best_distance:
                best_distance = distance
                best_match = user

        if compared == 0:
            logger.info("Face NOT matched — no valid enrolled embeddings to compare")
            return None, None

        if best_match and best_distance <= threshold:
            logger.info("Face MATCHED user_id=%s distance=%.3f", best_match["id"], best_distance)
            return best_match["id"], best_match.get("full_name") or best_match.get("username")

        logger.info(
            "Face NOT matched — best_distance=%.3f threshold=%.1f (compared %d faces)",
            best_distance, threshold, compared,
        )
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
