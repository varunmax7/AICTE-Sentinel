"""Field-level encryption, lookup hashing, and JWT helpers (IMPLEMENTATION.md §17).

- Phone/email are encrypted at rest (Fernet) and matched via a SHA-256 lookup
  hash, so we never store or query plaintext PII.
- JWTs are signed HS256 with `JWT_SECRET`; access tokens are short-lived,
  refresh tokens longer-lived, both delivered as httpOnly cookies by the
  auth router (never read from JS).
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta
from typing import Any, Literal

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.clock import now
from app.core.config import Settings, get_settings


def _fernet(settings: Settings) -> Fernet:
    # FIELD_ENCRYPTION_KEY is an arbitrary secret string in .env; Fernet needs a
    # 32-byte urlsafe-base64 key, so derive one deterministically via SHA-256.
    derived = hashlib.sha256(settings.FIELD_ENCRYPTION_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_field(value: str, *, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return _fernet(settings).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_field(token: str, *, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    try:
        return _fernet(settings).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Could not decrypt field — wrong key or corrupt data.") from exc


def normalize_identifier(identifier: str) -> str:
    """Normalizes a phone/email for hashing: lowercase emails, strip whitespace
    from phone numbers. Does not validate shape — callers pick the right kind.
    """
    identifier = identifier.strip()
    return identifier.lower() if "@" in identifier else identifier


def hash_identifier(identifier: str) -> str:
    return hashlib.sha256(normalize_identifier(identifier).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

TokenType = Literal["access", "refresh"]


def create_token(
    *, user_id: str, role: str, token_type: TokenType, settings: Settings | None = None
) -> str:
    settings = settings or get_settings()
    ttl = (
        timedelta(minutes=settings.JWT_ACCESS_TTL_MIN)
        if token_type == "access"
        else timedelta(days=settings.JWT_REFRESH_TTL_DAYS)
    )
    issued_at = now()
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "type": token_type,
        "iat": issued_at,
        "exp": issued_at + ttl,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


ACCESS_COOKIE = "acp_access"
REFRESH_COOKIE = "acp_refresh"


def access_cookie_max_age(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    return settings.JWT_ACCESS_TTL_MIN * 60


def refresh_cookie_max_age(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    return settings.JWT_REFRESH_TTL_DAYS * 24 * 60 * 60


def utcnow_naive() -> datetime:
    return now().replace(tzinfo=None)
