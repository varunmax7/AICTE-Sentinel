"""`LLMClient` (IMPLEMENTATION.md §14): "provider switch, JSON-schema-
constrained output, retry, timeout, token logging, and a `DEMO_MODE` cache
(same input → cached output)".

`complete` is the one entry point every AI-text feature (deficiency
letters now; e-case summaries, show-cause drafts, committee minutes in
later phases) is meant to go through. In `DEMO_MODE` — or whenever no
`LLM_API_KEY` is configured, which is always true in this sandbox — it
never makes a network call: it returns the caller-supplied deterministic
fallback and caches by `(system, prompt)` so repeated calls with the same
input are instant and identical, exactly as the spec asks. The real
provider branches (`gemini`/`anthropic`/`openai`) are implemented against
each provider's plain REST API (no extra SDK dependency) but are
unexercised without real credentials — same caveat as `OtpProvider`'s
non-demo branch in Phase P1 (see docs/DECISIONS.md).
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_DEMO_CACHE: dict[str, str] = {}


def _cache_key(system: str | None, prompt: str) -> str:
    return hashlib.sha256(f"{system or ''}\n{prompt}".encode()).hexdigest()


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def complete(
        self,
        *,
        prompt: str,
        system: str | None = None,
        demo_fallback: Callable[[], str],
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
    ) -> str:
        if self.settings.DEMO_MODE or not self.settings.LLM_API_KEY:
            key = _cache_key(system, prompt)
            if key not in _DEMO_CACHE:
                _DEMO_CACHE[key] = demo_fallback()
            return _DEMO_CACHE[key]

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return await self._call_provider(
                    prompt=prompt, system=system, timeout_seconds=timeout_seconds
                )
            except Exception as exc:  # noqa: BLE001 - retried below, logged and raised if exhausted
                last_error = exc
                logger.warning(
                    "LLMClient call failed (attempt %d/%d)", attempt + 1, max_retries + 1
                )
        assert last_error is not None
        raise last_error

    async def _call_provider(
        self, *, prompt: str, system: str | None, timeout_seconds: float
    ) -> str:
        provider = self.settings.LLM_PROVIDER
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            if provider == "anthropic":
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.settings.LLM_API_KEY,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": self.settings.LLM_MODEL or "claude-haiku-4-5",
                        "max_tokens": 1024,
                        "system": system or "",
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                text: str = data["content"][0]["text"]
                return text
            if provider == "openai":
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.LLM_API_KEY}"},
                    json={
                        "model": self.settings.LLM_MODEL or "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system or ""},
                            {"role": "user", "content": prompt},
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                openai_text: str = data["choices"][0]["message"]["content"]
                return openai_text
            # gemini
            model = self.settings.LLM_MODEL or "gemini-2.5-flash"
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": self.settings.LLM_API_KEY},
                json={"contents": [{"parts": [{"text": f"{system or ''}\n\n{prompt}"}]}]},
            )
            resp.raise_for_status()
            data = resp.json()
            gemini_text: str = data["candidates"][0]["content"]["parts"][0]["text"]
            return gemini_text
