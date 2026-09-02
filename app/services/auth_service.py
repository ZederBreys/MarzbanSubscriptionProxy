import time
import random
from typing import Optional

import app.core.config as cfg
from app.core.security import (
    hash_password,
    verify_password,
    generate_token,
    hash_token,
)
from app.database.queries import (
    get_admin_by_login,
    get_admin_by_id,
    update_admin_last_login,
    update_admin_password,
    create_session,
    get_session_by_hash,
    update_session_access,
    delete_session,
    delete_sessions_for_admin,
)


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class RateLimitError(AuthError):
    def __init__(self):
        super().__init__("Too many login attempts. Try again later.", 429)


_login_attempts: dict[str, list[float]] = {}


def _check_brute_force(ip: str, login: str) -> None:
    key = f"{ip}:{login}"
    now = time.time()
    attempts = [t for t in _login_attempts.get(key, []) if now - t < cfg.BRUTE_FORCE_WINDOW]
    _login_attempts[key] = attempts
    if len(attempts) >= cfg.BRUTE_FORCE_MAX_ATTEMPTS:
        raise RateLimitError()


def _record_failed_attempt(ip: str, login: str) -> None:
    key = f"{ip}:{login}"
    _login_attempts.setdefault(key, []).append(time.time())


def _clear_attempts(ip: str, login: str) -> None:
    key = f"{ip}:{login}"
    _login_attempts.pop(key, None)


def login(login: str, password: str, ip_address: str) -> dict:
    _check_brute_force(ip_address, login)

    # Random delay to mitigate timing/user enumeration
    time.sleep(random.uniform(0.1, 0.5))

    admin = get_admin_by_login(login)
    if not admin or not verify_password(admin["password_hash"], password):
        _record_failed_attempt(ip_address, login)
        raise AuthError("Invalid login or password.", 401)

    _clear_attempts(ip_address, login)

    session_token = generate_token()
    csrf_token = generate_token()
    session_hash = hash_token(session_token)
    csrf_hash = hash_token(csrf_token)
    expires_at = time.time() + cfg.SESSION_TTL

    create_session(
        session_hash=session_hash,
        admin_id=admin["id"],
        ip_address=ip_address,
        csrf_token_hash=csrf_hash,
        expires_at=expires_at,
    )

    now = time.time()
    update_admin_last_login(admin["id"], ip_address)

    return {
        "session_token": session_token,
        "csrf_token": csrf_token,
        "admin": {
            "login": admin["login"],
            "last_login_at": now,
            "last_login_ip": ip_address,
        },
    }


def verify_session(session_token: str) -> Optional[dict]:
    session_hash = hash_token(session_token)
    session = get_session_by_hash(session_hash)
    if not session:
        return None

    now = time.time()
    if session["expires_at"] < now:
        delete_session(session_hash)
        return None

    return session


def refresh_session_if_needed(session_hash: str, last_accessed_at: float) -> bool:
    now = time.time()
    if now - last_accessed_at > cfg.SESSION_REFRESH_INTERVAL:
        new_expires = now + cfg.SESSION_TTL
        update_session_access(session_hash, new_expires, now)
        return True
    return False


def do_logout(session_token: str) -> None:
    session_hash = hash_token(session_token)
    delete_session(session_hash)


def do_logout_all(admin_id: int) -> int:
    return delete_sessions_for_admin(admin_id)


def change_password(admin_id: int, old_password: str, new_password: str) -> None:
    admin = get_admin_by_id(admin_id)
    if not admin:
        raise AuthError("Admin not found.", 401)

    if not verify_password(admin["password_hash"], old_password):
        raise AuthError("Current password is incorrect.", 401)

    new_hash = hash_password(new_password)
    update_admin_password(admin_id, new_hash)
