import threading
import time
from functools import wraps
from flask import request, jsonify

_LOCK = threading.Lock()
_BUCKETS = {}


def rate_limit(max_requests=30, per_seconds=60):
    """Small local-process rate limiter for sensitive/costly endpoints."""
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            key = (request.remote_addr or "unknown", request.endpoint or fn.__name__)
            now = time.monotonic()
            with _LOCK:
                items = [t for t in _BUCKETS.get(key, []) if now - t < per_seconds]
                if len(items) >= max_requests:
                    return jsonify({"error": f"Rate limit reached. Try again in a moment."}), 429
                items.append(now)
                _BUCKETS[key] = items
            return fn(*args, **kwargs)
        return wrapped
    return decorate
