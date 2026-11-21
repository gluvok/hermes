from __future__ import annotations

import functools
import os
import secrets
import threading
import time
from collections.abc import Callable
from typing import Any

from flask import jsonify, request

SUPERADMIN_USER = os.getenv("SUPERADMIN_USER", "superadmin")
SUPERADMIN_PASS = os.getenv("SUPERADMIN_PASS", "")
SESSION_LIFETIME_SECONDS = 7200.0  # 2 hours
RATE_LIMIT_WINDOW_SECONDS = 60.0
MAX_FAILED_LOGIN_ATTEMPTS = 5

_active_sessions: dict[str, float] = {}
_session_lock = threading.Lock()

# ponytail: keyed by IP, pruned per key on check; a LAN host cycling IPs can grow it, add a size cap if that's ever seen
_failed_login_attempts: dict[str, list[float]] = {}
_login_lock = threading.Lock()


def create_session_token() -> str:
    """Generates a cryptographically secure session token with sliding expiration."""
    token = secrets.token_hex(32)
    with _session_lock:
        _active_sessions[token] = time.time() + SESSION_LIFETIME_SECONDS
    return token


def validate_session_token(token: str | None) -> bool:
    """Validates session token and slides expiration window if active."""
    if not token:
        return False

    now = time.time()
    with _session_lock:
        exp = _active_sessions.get(token)
        if exp is None:
            return False

        if exp > now:
            _active_sessions[token] = now + SESSION_LIFETIME_SECONDS
            return True

        del _active_sessions[token]
        return False


def revoke_session_token(token: str | None) -> None:
    """Removes a single session token; unknown or empty tokens are ignored."""
    if token:
        with _session_lock:
            _active_sessions.pop(token, None)


def is_rate_limited(key: str = "") -> bool:
    """Brute force mitigation: max 5 failed logins per client key within 60 seconds."""
    now = time.time()
    with _login_lock:
        recent = [
            t for t in _failed_login_attempts.get(key, [])
            if now - t < RATE_LIMIT_WINDOW_SECONDS
        ]
        if recent:
            _failed_login_attempts[key] = recent
        else:
            _failed_login_attempts.pop(key, None)
        return len(recent) >= MAX_FAILED_LOGIN_ATTEMPTS


def record_failed_login(key: str = "") -> None:
    """Records a failed authentication attempt timestamp for a client key."""
    with _login_lock:
        _failed_login_attempts.setdefault(key, []).append(time.time())


def require_runtime_secrets() -> None:
    """Refuse to start without the secrets that used to have committed defaults (#33)."""
    missing = [n for n in ("SUPERADMIN_PASS", "HERMES_HOTSPOT_PASS") if not os.getenv(n)]
    if missing:
        raise SystemExit(f"Missing required environment: {', '.join(missing)} (see data/hermes.env)")


def verify_credentials(userid: str, password: str) -> bool:
    """Constant-time verification of superadmin credentials."""
    if not SUPERADMIN_PASS:
        return False
    user_ok = secrets.compare_digest(userid.strip(), SUPERADMIN_USER)
    pass_ok = secrets.compare_digest(password, SUPERADMIN_PASS)
    return user_ok and pass_ok


def extract_auth_token() -> str:
    """Extracts bearer token from Authorization header or X-Auth-Token header."""
    auth_hdr = request.headers.get("Authorization", "")
    if auth_hdr.startswith("Bearer "):
        return auth_hdr[7:].strip()
    return request.headers.get("X-Auth-Token", "").strip()


def auth_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator ensuring request contains a valid superadmin session token."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = extract_auth_token()
        if not validate_session_token(token):
            return jsonify({
                "success": False,
                "error": "Unauthorized. Superadmin credentials required.",
            }), 401
        return func(*args, **kwargs)

    return wrapper


def reset_auth_state() -> None:
    """Resets session tokens and failed login counter (useful for testing)."""
    with _session_lock:
        _active_sessions.clear()
    with _login_lock:
        _failed_login_attempts.clear()
