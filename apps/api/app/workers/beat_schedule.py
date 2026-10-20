"""Celery Beat schedule, grown phase by phase (§4.1, §10.3). Task names are
referenced as strings so this module has no import-time dependency on the
task modules themselves.
"""

from __future__ import annotations

from typing import Any

beat_schedule: dict[str, dict[str, Any]] = {
    "outbox-publish-pending": {
        "task": "app.workers.tasks.outbox.publish_pending",
        "schedule": 5.0,  # seconds — safety net; the API also nudges this task on demand
    },
}
