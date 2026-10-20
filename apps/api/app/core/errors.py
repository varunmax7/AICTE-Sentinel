"""Standard error envelope for every API response (IMPLEMENTATION.md §13 intro):
`{ "error": { "code": "...", "params": {...} } }`. Routers raise
`HTTPException(status, detail={"code": ..., "params": {...}})`; anything else
(including FastAPI's own validation errors) is normalized here too, so the
frontend's i18n error-translation layer always has one shape to work with.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _envelope(code: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "params": params or {}}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            body = _envelope(detail["code"], detail.get("params"))
        else:
            body = _envelope("HTTP_ERROR", {"message": str(detail)})
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(body),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        body = _envelope("VALIDATION_ERROR", {"errors": jsonable_encoder(exc.errors())})
        return JSONResponse(status_code=422, content=body)
