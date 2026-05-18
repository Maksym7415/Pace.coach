"""
Simple in-memory sliding-window rate limits for auth endpoints.

Suitable for single-process deployments; use Redis or similar for horizontal scale.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import DefaultDict, List

_lock = threading.Lock()
_buckets: DefaultDict[str, List[float]] = defaultdict(list)

# Defaults tuned for basic abuse protection without frustrating real users.
LOGIN_WINDOW_SEC = 15 * 60
LOGIN_MAX_PER_WINDOW = 30

REGISTER_WINDOW_SEC = 60 * 60
REGISTER_MAX_PER_WINDOW = 15

FORGOT_PASSWORD_WINDOW_SEC = 60 * 60
FORGOT_PASSWORD_MAX_PER_WINDOW = 10


def _prune(bucket: List[float], now: float, window_sec: float) -> None:
    cutoff = now - window_sec
    bucket[:] = [t for t in bucket if t > cutoff]


def is_rate_limited(key: str, max_requests: int, window_sec: float) -> bool:
    """
    Return True if this key has exceeded max_requests in the last window_sec seconds.
    Otherwise record this attempt and return False.
    """
    now = time.monotonic()
    with _lock:
        bucket = _buckets[key]
        _prune(bucket, now, window_sec)
        if len(bucket) >= max_requests:
            return True
        bucket.append(now)
    return False
