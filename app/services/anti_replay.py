"""Lightweight anti-replay checks for repeated frames and request bursts."""

import hashlib
import logging
import time
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

_recent_frame_hashes = deque(maxlen=500)
_recent_attempts_by_identity = defaultdict(lambda: deque(maxlen=20))

FRAME_HASH_WINDOW_SECONDS = 30
DUPLICATE_FRAME_THRESHOLD = 2
ATTEMPT_VELOCITY_WINDOW_SECONDS = 60
ATTEMPT_VELOCITY_LIMIT = 8


def frame_fingerprint(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def is_suspected_replay(image_bytes: bytes) -> bool:
    if not image_bytes:
        return False

    now = time.time()
    fp = frame_fingerprint(image_bytes)

    while _recent_frame_hashes and now - _recent_frame_hashes[0][1] > FRAME_HASH_WINDOW_SECONDS:
        _recent_frame_hashes.popleft()

    count = sum(1 for h, _ in _recent_frame_hashes if h == fp)
    _recent_frame_hashes.append((fp, now))

    if count >= DUPLICATE_FRAME_THRESHOLD:
        logger.warning("Suspected frame replay: identical frame seen %d times in %ds window", count + 1, FRAME_HASH_WINDOW_SECONDS)
        return True
    return False


def is_over_velocity_limit(user_id) -> bool:
    if user_id is None:
        return False

    now = time.time()
    attempts = _recent_attempts_by_identity[user_id]
    while attempts and now - attempts[0] > ATTEMPT_VELOCITY_WINDOW_SECONDS:
        attempts.popleft()
    attempts.append(now)
    return len(attempts) > ATTEMPT_VELOCITY_LIMIT
