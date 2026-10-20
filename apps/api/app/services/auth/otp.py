"""Twilio Verify OTP adapter, with a `DEMO_MODE` bypass (IMPLEMENTATION.md
§11.4, §18): in demo mode no SMS/WhatsApp is sent and `DEMO_FIXED_OTP` is the
only accepted code — this is how the login flow is demoable without live
Twilio credentials or real phones.
"""

from __future__ import annotations

import asyncio

from twilio.rest import Client

from app.core.config import Settings, get_settings


class OtpProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _client(self) -> Client:
        return Client(self.settings.TWILIO_ACCOUNT_SID, self.settings.TWILIO_AUTH_TOKEN)

    async def send(self, identifier: str, *, channel: str = "sms") -> str:
        """Returns a provider reference: the Twilio Verify SID, or `"demo"`."""
        if self.settings.DEMO_MODE:
            return "demo"
        return await asyncio.to_thread(self._send_sync, identifier, channel)

    def _send_sync(self, identifier: str, channel: str) -> str:
        verification = (
            self._client()
            .verify.v2.services(self.settings.TWILIO_VERIFY_SERVICE_SID)
            .verifications.create(to=identifier, channel=channel)
        )
        sid: str = verification.sid
        return sid

    async def check(self, identifier: str, code: str) -> bool:
        if self.settings.DEMO_MODE:
            return code == self.settings.DEMO_FIXED_OTP
        return await asyncio.to_thread(self._check_sync, identifier, code)

    def _check_sync(self, identifier: str, code: str) -> bool:
        check = (
            self._client()
            .verify.v2.services(self.settings.TWILIO_VERIFY_SERVICE_SID)
            .verification_checks.create(to=identifier, code=code)
        )
        status: str = check.status
        return status == "approved"
