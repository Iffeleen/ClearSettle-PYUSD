import time

_FAILURES = {}
MAX_FAILURES = 5
WINDOW_SECONDS = 300


def _recent(key):
    now = time.time()
    recent = [t for t in _FAILURES.get(key, []) if now - t < WINDOW_SECONDS]
    _FAILURES[key] = recent
    return recent


def is_blocked(key):
    return len(_recent(key)) >= MAX_FAILURES


def record_failure(key):
    _recent(key).append(time.time())


def clear(key):
    _FAILURES.pop(key, None)
