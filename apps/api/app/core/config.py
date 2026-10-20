"""Application configuration loaded from environment variables (`.env`).

Every setting here mirrors a variable documented in `IMPLEMENTATION.md` §6
(`.env.example`). Nothing is hardcoded — see §0.2 rule 3. Secrets have no
default beyond the obviously-fake placeholders shipped in `.env.example`
itself, so a production deployment that forgets to override them is at least
not silently using a *different* unseen default.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---------- General ----------
    APP_ENV: Literal["development", "demo", "production"] = "development"
    DEMO_MODE: bool = True
    DEMO_FIXED_OTP: str = "123456"
    PUBLIC_WEB_URL: str = "http://localhost:3000"
    PUBLIC_API_URL: str = "http://localhost:8000"
    PUBLIC_VOICE_URL: str = "http://localhost:8010"
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # ---------- Security ----------
    JWT_SECRET: str = "change-me"
    JWT_ACCESS_TTL_MIN: int = 15
    JWT_REFRESH_TTL_DAYS: int = 7
    INTERNAL_SERVICE_TOKEN: str = "change-me-voice-to-core"
    FIELD_ENCRYPTION_KEY: str = "change-me-32-bytes"

    # ---------- Data ----------
    DATABASE_URL: str = "postgresql+asyncpg://acp:acp@localhost:5432/acp"
    REDIS_URL: str = "redis://localhost:6379/0"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minio"
    S3_SECRET_KEY: str = "minio123"
    S3_BUCKET: str = "acp"

    # ---------- AI ----------
    LLM_PROVIDER: Literal["gemini", "anthropic", "openai"] = "gemini"
    LLM_MODEL: str = ""
    LLM_MODEL_VISION: str = ""
    LLM_API_KEY: str = ""
    EMBEDDING_MODEL: str = ""
    OCR_FALLBACK: Literal["tesseract", "paddle"] = "tesseract"

    # ---------- Twilio ----------
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_VERIFY_SERVICE_SID: str = ""
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"
    TWILIO_SMS_FROM: str = ""
    TWILIO_VOICE_NUMBER: str = ""
    TWILIO_MESSAGING_STATUS_CALLBACK: str = ""
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@example.com"
    SENDGRID_INBOUND_DOMAIN: str = "reply.example.com"
    SENDGRID_WEBHOOK_PUBLIC_KEY: str = ""

    # ---------- Voice (Track V) ----------
    VOICE_STT_PROVIDER: str = "google"
    VOICE_TTS_PROVIDER: str = "google"
    SARVAM_API_KEY: str = ""
    CALL_HOURS_START: str = "10:00"
    CALL_HOURS_END: str = "18:00"
    CALL_MAX_ATTEMPTS: int = 3
    CALL_RETRY_GAP_MIN: int = 120

    @property
    def is_demo(self) -> bool:
        return self.DEMO_MODE


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Use the `SettingsDep` FastAPI dependency instead
    of calling this directly from request-handling code, so tests can override it.
    """
    return Settings()
