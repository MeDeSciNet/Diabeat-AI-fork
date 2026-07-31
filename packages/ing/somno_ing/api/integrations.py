"""Integration preview endpoints (PRD 8.2). Mock implementations only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..db import AlertRow, NightlyRiskRow, Session as SessionRow, db_session
from ..integrations import get_fhir_exporter, get_nurse_call
from .deps import Principal, require

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])


@router.get("/fhir/observation/{session_id}")
def fhir_observation(session_id: str, principal: Principal = Depends(require("researcher"))):
    with db_session() as db:
        session = db.get(SessionRow, session_id)
        risk = db.get(NightlyRiskRow, session_id)
        if session is None or risk is None:
            raise HTTPException(404, "session not analysed")
        payload = {
            "subject_code": session.subject_code,
            "started_at": session.started_at.isoformat() if session.started_at else None,
        }
        risk_payload = {
            "score": risk.score,
            "band": risk.band,
            "components": risk.components or {},
        }
    return get_fhir_exporter().observation(payload, risk_payload)


@router.get("/fhir/detected-issue/{alert_id}")
def fhir_detected_issue(alert_id: str, principal: Principal = Depends(require("researcher"))):
    with db_session() as db:
        row = db.get(AlertRow, alert_id)
        if row is None:
            raise HTTPException(404, "unknown alert")
        payload = {
            "rule_id": row.rule_id,
            "title": row.title,
            "severity": row.severity,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "recommended_actions": row.recommended_actions or [],
        }
    return get_fhir_exporter().detected_issue(payload)


@router.post("/nurse-call/{alert_id}")
def nurse_call_preview(alert_id: str, principal: Principal = Depends(require("researcher"))):
    """Shows what would be sent. Always returns delivered=false in v1."""
    with db_session() as db:
        row = db.get(AlertRow, alert_id)
        if row is None:
            raise HTTPException(404, "unknown alert")
        payload = {
            "bed_id": row.bed_id,
            "title": row.title,
            "recommended_actions": row.recommended_actions or [],
        }
    return get_nurse_call().notify(payload)
