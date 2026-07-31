"""FastAPI application (PRD 6.6)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ..db import init_db
from ..detect.rule_based import DETECTOR_VERSION
from .deps import Principal, current_principal, require

log = logging.getLogger(__name__)

RUO_NOTICE = (
    "Research use only. This system does not provide a diagnosis and must not be "
    "used as the basis for clinical or treatment decisions."
)

app = FastAPI(
    title="SomnoSwallow ING",
    version="1.0.0",
    description=(
        "Ingest and overnight analysis service.\n\n"
        f"**{RUO_NOTICE}**\n\n"
        "Analysis is batch and post-hoc by design; this service is not an active "
        "patient monitor and produces no real-time alarms."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

meta = APIRouter(tags=["meta"])


@meta.get("/health")
def health() -> dict:
    return {"status": "ok", "detector_version": DETECTOR_VERSION, "notice": RUO_NOTICE}


@meta.get("/v1/meta")
def service_meta(principal: Principal = Depends(current_principal)) -> dict:
    from ..alerts import VALID_ACTIONS
    from ..risk import RISK_VERSION

    return {
        "detector_version": DETECTOR_VERSION,
        "risk_version": RISK_VERSION,
        "actions": sorted(VALID_ACTIONS),
        "notice": RUO_NOTICE,
        "role": principal.role,
    }


@meta.get("/v1/eval/detection", tags=["eval"])
def eval_detection(
    session_id: str,
    tolerance_ms: int = Query(750, ge=50, le=5000),
    principal: Principal = Depends(require("researcher")),
) -> dict:
    """Detection performance against SIM ground truth. Development instrument."""
    from ..devtools import evaluate_session

    try:
        return evaluate_session(session_id, tolerance_ms)
    except Exception as exc:
        raise HTTPException(404, f"cannot evaluate {session_id}: {exc}") from None


@meta.get("/v1/audit", tags=["audit"])
def audit_log(
    bed_id: str | None = None,
    limit: int = Query(200, le=1000),
    principal: Principal = Depends(require("researcher", "nurse")),
) -> dict:
    from ..audit import entries, verify_chain

    intact, bad = verify_chain()
    return {"intact": intact, "first_bad_id": bad, "entries": entries(bed_id, limit)}


def create_app() -> FastAPI:
    from . import alerts as alerts_router
    from . import beds as beds_router
    from . import integrations as integrations_router
    from . import sessions as sessions_router

    app.include_router(meta)
    app.include_router(sessions_router.router)
    app.include_router(alerts_router.router)
    app.include_router(beds_router.router)
    app.include_router(integrations_router.router)
    return app


@app.on_event("startup")
def _startup() -> None:
    try:
        init_db()
    except Exception:  # pragma: no cover - database may lag the API container
        log.exception("init_db failed at startup; will retry on first request")


create_app()
