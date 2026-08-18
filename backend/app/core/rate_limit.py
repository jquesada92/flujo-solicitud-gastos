import math
import threading
import time
from collections import deque
from typing import NamedTuple

import jwt

from app.core.config import get_settings


class RatePolicy(NamedTuple):
    name: str
    limit: int
    window_seconds: int


settings = get_settings()
READ_POLICY = RatePolicy('read', settings.user_read_rate_limit, 60)
WRITE_POLICY = RatePolicy('write', settings.user_write_rate_limit, 60)
UPLOAD_POLICY = RatePolicy('upload', settings.user_upload_rate_limit, 60)
SENSITIVE_POLICY = RatePolicy('sensitive', settings.user_sensitive_rate_limit, 60)

_requests: dict[str, deque[float]] = {}
_lock = threading.Lock()


def authenticated_subject(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith('bearer '):
        return None
    try:
        token = authorization.split(None, 1)[1]
        payload = jwt.decode(token, get_settings().secret_key, algorithms=['HS256'])
        return str(int(payload['sub']))
    except (jwt.PyJWTError, KeyError, ValueError, IndexError):
        return None


def policy_for_request(method: str, path: str) -> RatePolicy:
    method = method.upper()
    if method in ('GET', 'HEAD'):
        return READ_POLICY
    if '/attachments' in path or path.endswith('/close') or path.endswith('/invoice'):
        return UPLOAD_POLICY
    sensitive = (
        path.startswith('/api/approvals/'),
        path.endswith('/change-password'),
        path.endswith('/regenerate-password'),
        path.endswith('/bulk'),
        path.startswith('/api/iam/'),
    )
    return SENSITIVE_POLICY if any(sensitive) else WRITE_POLICY


def consume_user_request(subject: str, policy: RatePolicy, now: float | None = None) -> tuple[bool, int, int]:
    current = time.monotonic() if now is None else now
    cutoff = current - policy.window_seconds
    key = f'{subject}:{policy.name}'
    with _lock:
        events = _requests.setdefault(key, deque())
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= policy.limit:
            retry_after = max(1, math.ceil(policy.window_seconds - (current - events[0])))
            return False, 0, retry_after
        events.append(current)
        return True, policy.limit - len(events), 0


def clear_rate_limits() -> None:
    with _lock:
        _requests.clear()
