"""Alert queue, acknowledgement, dismissal and care-action recording."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..alerts import VALID_ACTIONS
from ..audit import record as audit_record
from ..db import AlertRow, CareActionRow, db_session
from .deps import Principal, current_principal, require

router = APIRouter(prefix="/v1", tags=["alerts"])

DISMISS_REASONS = ("poor_data_quality", "known_condition", "false_positive", "other")


class DismissBody(BaseModel):
    reason: str = Field(description="One of " + ", ".join(DISMISS_REASONS))
    note: str | None = None


class CareActionBody(BaseModel):
    subject_code: str
    action: str
    session_id: str | None = None
    alert_id: str | None = None
    note: str | None = None


@router.get("/alerts")
def list_alerts(
    status: str | None = None,
    bed_id: str | None = None,
    subject_code: str | None = None,
    session_id: str | None = None,
    severity: str | None = None,
    limit: int = Query(200, le=1000),
    principal: Principal = Depends(current_principal),
):
    with db_session() as db:
        q = select(AlertRow).order_by(AlertRow.created_at.desc()).limit(limit)
        for column, value in (
            (AlertRow.status, status),
            (AlertRow.bed_id, bed_id),
            (AlertRow.subject_code, subject_code),
            (AlertRow.session_id, session_id),
            (AlertRow.severity, severity),
        ):
            if value:
                q = q.where(column == value)
        return [_alert_dict(r) for r in db.scalars(q)]


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str, principal: Principal = Depends(current_principal)):
    with db_session() as db:
        row = db.get(AlertRow, alert_id)
        if row is None:
            raise HTTPException(404, "unknown alert")
        return _alert_dict(row)


@router.post("/alerts/{alert_id}/ack")
def ack_alert(
    alert_id: str, principal: Principal = Depends(require("nurse", "caregiver", "researcher"))
):
    with db_session() as db:
        row = db.get(AlertRow, alert_id)
        if row is None:
            raise HTTPException(404, "unknown alert")
        if row.status == "dismissed":
            raise HTTPException(409, "alert was dismissed")
        row.status = "acknowledged"
        row.acknowledged_by = principal.actor_id
        row.acknowledged_at = datetime.now(UTC)
        out = _alert_dict(row)
    audit_record(principal.actor_id, "alert.ack", {"alert_id": alert_id}, bed_id=out["bed_id"])
    return out


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: str,
    body: DismissBody,
    principal: Principal = Depends(require("nurse", "caregiver", "researcher")),
):
    """Dismissal always records a reason.

    PRD 8.1 S-4 calls this the core product-improvement dataset: the distribution
    of dismissal reasons is the only direct signal about false-positive rate that
    a research deployment gets.
    """
    if body.reason not in DISMISS_REASONS:
        raise HTTPException(422, f"reason must be one of {DISMISS_REASONS}")
    with db_session() as db:
        row = db.get(AlertRow, alert_id)
        if row is None:
            raise HTTPException(404, "unknown alert")
        row.status = "dismissed"
        row.dismissed_by = principal.actor_id
        row.dismissed_at = datetime.now(UTC)
        row.dismiss_reason = body.reason
        row.dismiss_note = body.note
        out = _alert_dict(row)
    audit_record(
        principal.actor_id,
        "alert.dismiss",
        {"alert_id": alert_id, "reason": body.reason, "note": body.note},
        bed_id=out["bed_id"],
    )
    return out


@router.get("/alerts-stats/dismissals")
def dismissal_stats(principal: Principal = Depends(require("researcher", "nurse"))):
    """Exportable dismissal breakdown, by rule and reason."""
    with db_session() as db:
        rows = db.scalars(select(AlertRow).where(AlertRow.status == "dismissed")).all()
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        out.setdefault(r.rule_id, {}).setdefault(r.dismiss_reason or "unspecified", 0)
        out[r.rule_id][r.dismiss_reason or "unspecified"] += 1
    return {"by_rule": out, "total": len(rows)}


@router.post("/care-actions", status_code=201)
def record_care_action(
    body: CareActionBody,
    principal: Principal = Depends(require("nurse", "caregiver")),
):
    if body.action not in VALID_ACTIONS:
        raise HTTPException(422, f"unknown action {body.action!r}")
    action_id = str(uuid.uuid4())
    with db_session() as db:
        db.add(
            CareActionRow(
                id=action_id,
                subject_code=body.subject_code,
                session_id=body.session_id,
                alert_id=body.alert_id,
                action=body.action,
                performed_by=principal.actor_id,
                performed_at=datetime.now(UTC),
                note=body.note,
            )
        )
    audit_record(
        principal.actor_id,
        "care_action.record",
        {"action": body.action, "subject_code": body.subject_code, "alert_id": body.alert_id},
    )
    return {"id": action_id, "action": body.action}


@router.get("/care-actions")
def list_care_actions(
    subject_code: str | None = None,
    limit: int = Query(200, le=1000),
    principal: Principal = Depends(current_principal),
):
    with db_session() as db:
        q = select(CareActionRow).order_by(CareActionRow.performed_at.desc()).limit(limit)
        if subject_code:
            q = q.where(CareActionRow.subject_code == subject_code)
        return [
            {
                "id": r.id,
                "subject_code": r.subject_code,
                "session_id": r.session_id,
                "alert_id": r.alert_id,
                "action": r.action,
                "performed_by": r.performed_by,
                "performed_at": r.performed_at.isoformat() if r.performed_at else None,
                "note": r.note,
            }
            for r in db.scalars(q)
        ]


def _alert_dict(r: AlertRow) -> dict:
    return {
        "id": r.id,
        "session_id": r.session_id,
        "subject_code": r.subject_code,
        "bed_id": r.bed_id,
        "rule_id": r.rule_id,
        "severity": r.severity,
        "status": r.status,
        "title": r.title,
        "body": r.body,
        "recommended_actions": r.recommended_actions or [],
        "dedup_key": r.dedup_key,
        "repeat_nights": r.repeat_nights,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "deliver_after": r.deliver_after.isoformat() if r.deliver_after else None,
        "acknowledged_by": r.acknowledged_by,
        "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
        "dismissed_by": r.dismissed_by,
        "dismissed_at": r.dismissed_at.isoformat() if r.dismissed_at else None,
        "dismiss_reason": r.dismiss_reason,
        "dismiss_note": r.dismiss_note,
        "context": r.context or {},
    }
