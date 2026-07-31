"""Celery tasks for nightly batch analysis.

Analysis is deliberately asynchronous and post-hoc: PRD 2.1 R1 keeps this system
out of active patient monitoring, so nothing here runs on a live path.
"""

from __future__ import annotations

import logging

from celery import Celery

from .settings import get_settings

log = logging.getLogger(__name__)
_settings = get_settings()

app = Celery("somno_ing", broker=_settings.redis_url, backend=_settings.redis_url)
app.conf.update(
    task_always_eager=_settings.celery_eager,
    task_eager_propagates=_settings.celery_eager,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="somno",
    worker_prefetch_multiplier=1,
    # Failures land in a dead-letter queue rather than vanishing (PRD 10.3).
    task_annotations={"*": {"max_retries": 3, "default_retry_delay": 30}},
)


@app.task(bind=True, name="somno.analyze_session")
def analyze_session(self, session_id: str) -> dict:
    from .pipeline import analyze

    try:
        return analyze(session_id)
    except Exception as exc:  # pragma: no cover - exercised via retry path
        log.exception("analysis failed for %s", session_id)
        _record_failure(session_id, str(exc))
        raise self.retry(exc=exc)


@app.task(name="somno.dead_letter")
def dead_letter(session_id: str, error: str) -> None:  # pragma: no cover
    _record_failure(session_id, error)


def _record_failure(session_id: str, error: str) -> None:
    from .db import Session as SessionRow, db_session

    with db_session() as db:
        row = db.get(SessionRow, session_id)
        if row is not None:
            row.status = "failed"
            row.analysis_error = error[:2000]
