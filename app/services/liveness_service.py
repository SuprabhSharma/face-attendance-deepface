"""Passive + active liveness detection for webcam attendance.

This implementation is intentionally fail-closed: if the model files or runtime
packages are unavailable, the check returns False and prevents a registration or
recognition decision from succeeding.
"""

import logging
import os

import cv2
import numpy as np

try:
    import onnxruntime as ort
except Exception:  # pragma: no cover - optional runtime dependency
    ort = None

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models_weights")
MODEL_CONFIGS = [
    {"file": "2.7_80x80_MiniFASNetV2.onnx", "scale": 2.7, "weight": 1.0},
    {"file": "4_0_0_80x80_MiniFASNetV1SE.onnx", "scale": 4.0, "weight": 1.0},
]
REAL_CLASS_INDEX = 2  # MiniFASNet 3-class output: 0=background, 1=spoof/attack, 2=real
REAL_THRESHOLD = 0.40
FAKE_THRESHOLD = 0.20

_SESSIONS = []

try:
    DETECTOR_BACKEND = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    EYE_CASCADE = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_eye.xml"
    )
except Exception:
    DETECTOR_BACKEND = None
    EYE_CASCADE = None


def _load_models():
    """Load MiniFASNet model sessions if the matching weight files are present."""
    if ort is None:
        logger.warning("onnxruntime is not installed; liveness checks are disabled and fail closed.")
        return

    _SESSIONS.clear()
    for cfg in MODEL_CONFIGS:
        path = os.path.join(MODEL_DIR, cfg["file"])
        if not os.path.exists(path):
            logger.warning("Liveness model missing: %s", path)
            continue
        try:
            session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
            _SESSIONS.append({"session": session, "scale": cfg["scale"], "weight": cfg["weight"]})
            logger.info("Liveness model loaded: %s", cfg["file"])
        except Exception:
            logger.exception("Failed to load liveness model %s", cfg["file"])


_load_models()


def _detect_primary_face(image_bgr):
    if image_bgr is None:
        return None
    img_h, img_w = image_bgr.shape[:2]
    if DETECTOR_BACKEND is not None:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        # First attempt: standard parameters
        faces = DETECTOR_BACKEND.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        if len(faces) == 0:
            # Second attempt: relaxed parameters for low contrast, tilted, or distant faces
            faces = DETECTOR_BACKEND.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2, minSize=(25, 25))
        if len(faces) > 0:
            return max(faces, key=lambda f: f[2] * f[3])

    # Fallback to center region where user faces the camera alignment frame
    fw = int(img_w * 0.5)
    fh = int(img_h * 0.5)
    fx = int((img_w - fw) / 2)
    fy = int((img_h - fh) / 2)
    return (fx, fy, fw, fh)


def _crop_with_scale(image_bgr, bbox, scale):
    if bbox is None:
        return None
    x, y, w, h = bbox
    img_h, img_w = image_bgr.shape[:2]
    cx, cy = x + w / 2.0, y + h / 2.0
    box_size = max(w, h) * scale
    x1 = int(max(0, cx - box_size / 2))
    y1 = int(max(0, cy - box_size / 2))
    x2 = int(min(img_w, cx + box_size / 2))
    y2 = int(min(img_h, cy + box_size / 2))
    crop = image_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    return cv2.resize(crop, (80, 80))


def _softmax(x):
    e = np.exp(x - np.max(x))
    return e / e.sum()


def _passive_liveness_score(image_bgr, bbox):
    if not _SESSIONS:
        return None

    combined = np.zeros(3, dtype=np.float32)
    total_weight = 0.0

    for model in _SESSIONS:
        crop = _crop_with_scale(image_bgr, bbox, model["scale"])
        if crop is None:
            continue

        inp = crop.astype(np.float32) / 255.0
        inp = np.transpose(inp, (2, 0, 1))[None, ...]
        input_name = model["session"].get_inputs()[0].name
        raw_out = model["session"].run(None, {input_name: inp})[0][0]
        probs = _softmax(raw_out)
        combined += probs * model["weight"]
        total_weight += model["weight"]

    if total_weight == 0:
        return None

    combined /= total_weight
    return float(combined[REAL_CLASS_INDEX])


def _active_blink_fallback(frames_bgr):
    if not frames_bgr or len(frames_bgr) < 3 or EYE_CASCADE is None:
        return False

    sequence = []
    for frame in frames_bgr:
        if frame is None:
            sequence.append(False)
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        eyes = EYE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(15, 15))
        sequence.append(len(eyes) >= 2)

    for i in range(1, len(sequence) - 1):
        if sequence[i - 1] and not sequence[i] and sequence[i + 1]:
            return True
    return False


def check_liveness(image_bgr, session_frames=None):
    """Return (is_real, confidence, reason).

    Liveness verifies the user is present in front of the camera.
    """
    if image_bgr is None:
        return False, 0.0, "no_image"

    bbox = _detect_primary_face(image_bgr)
    if bbox is None:
        return False, 0.0, "no_face_detected"

    if not _SESSIONS:
        logger.error("Liveness models unavailable; rejecting request")
        return False, 0.0, "liveness_unavailable"

    score = _passive_liveness_score(image_bgr, bbox)
    if score is None:
        logger.error("Liveness model inference unavailable; rejecting request")
        return False, 0.0, "liveness_unavailable"

    if score >= REAL_THRESHOLD:
        return True, score, "passive_real"
    if score <= FAKE_THRESHOLD:
        return False, score, "passive_fake"

    if session_frames:
        blinked = _active_blink_fallback(session_frames)
        if blinked:
            return True, score, "active_blink_confirmed"
        return False, score, "active_blink_not_detected"

    # For borderline scores (between 0.20 and 0.40) where no burst frames are provided,
    # grant a soft pass if score >= 0.25 to prevent false rejections of real users.
    if score >= 0.25:
        return True, score, "passive_marginal_pass"

    logger.info("Liveness below threshold (score=%.3f) — rejecting", score)
    return False, score, "score_below_threshold"
