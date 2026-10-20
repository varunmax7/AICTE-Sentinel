"""FastAPI entrypoint for the AI calling agent service (`apps/voice`, Track V — Rishanth).

Phase P0 ships a bare skeleton (`/health` only) so `docker compose up` and CI are
green end to end. Inbound/outbound TwiML, the ConversationRelay WebSocket, the
LLM agent brain and personas are built starting Phase V0 — see
IMPLEMENTATION.md §12 and §20.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="AICTE ACP — Voice Agent Service",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
