"""Celery application for background jobs (`workers` + `beat` services in
docker-compose). Phase P0 wires the app, broker and an empty beat schedule so
`worker`/`beat` containers start healthy; real tasks (deadline_scan,
send_notification, ocr_extract, reports, ml_score — see §4 and §19 Phase
P7/P9/P11) are registered in `app.workers.tasks` starting Phase P2+.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "acp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[],  # task modules are added here as they're implemented, phase by phase
)

celery_app.conf.update(
    timezone=settings.DEFAULT_TIMEZONE,
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

# Populated in app.workers.beat_schedule once there are tasks to schedule
# (e.g. deadline_scan every 60s, per §10.3).
celery_app.conf.beat_schedule = {}
