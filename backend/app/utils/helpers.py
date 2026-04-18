"""Utility helpers — image conversion and validation."""

import base64
import re

import cv2
import numpy as np


def base64_to_cv2(base64_str: str):
    """Convert a base64-encoded image string to an OpenCV BGR image.

    Handles data-URI prefixed strings (e.g. ``data:image/jpeg;base64,...``).
    Returns ``None`` if decoding fails.
    """
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        img_data = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def is_valid_email(email: str) -> bool:
    """Basic email format check."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))
