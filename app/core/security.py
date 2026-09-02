import hashlib
import secrets
from typing import Tuple

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerificationError, VerifyMismatchError):
        return False


def generate_token(length: int = 32) -> str:
    return secrets.token_hex(length)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def secure_compare(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)
