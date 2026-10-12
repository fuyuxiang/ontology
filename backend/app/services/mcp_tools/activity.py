"""Process-local in-flight MCP HTTP requests, not persistent client sessions."""
from contextlib import contextmanager
from threading import Lock

_lock = Lock()
_active = 0


@contextmanager
def track_request():
    global _active
    with _lock:
        _active += 1
    try:
        yield
    finally:
        with _lock:
            _active -= 1


def active_requests():
    with _lock:
        return _active
