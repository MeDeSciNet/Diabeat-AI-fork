"""Bed overview, shift summary and system health (STATION S-1, S-2, S-5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from ..db import AlertRow, Bed, Device, NightlyRiskRow, Session as SessionRow, aware, db_session
from .deps import Principal, current_principal

router = APIRouter(prefix="/v1", tags=["station"])

# Three states only. There is no red: red means "act now", and PRD 2.1 R1 keeps
# this system out of anything that implies urgency.
STATUS_LIGHT = {
    "insufficient_data": "grey",
    "low": "blue",
    "moderate": "blue",
    "elevated": "amber",
}
BAND_RANK = {"elevated": 3, "moderate": 2, "low": 1, "insufficient_data": 0, None: 0}

SHIFTS = {
    "night": (23, 7),
    "day": (7, 15),
    "evening": (15, 23),
}


@router.get("/beds")
def list_beds(principal: Principal = Depends(current_principal)):
    since = datetime.now(UTC) - timedelta(days=2)
    with db_session() as db:
        beds = db.scalars(select(Bed)).all()
        sessions = db.scalars(
            select(SessionRow).where(SessionRow.started_at >= since).order_by(SessionRow.started_at)
        ).all()
        latest: dict[str, SessionRow] = {}
        for s in sessions:
            if s.bed_id:
                latest[s.bed_id] = s
        risks = {r.session_id: r for r in db.scalars(select(NightlyRiskRow))}
        open_alerts = db.scalars(select(AlertRow).where(AlertRow.status == "open")).all()
        devices = {d.device_id: d for d in db.scalars(select(Device))}

        rows = []
        for bed in beds:
            s = latest.get(bed.bed_id)
            risk = risks.get(s.id) if s else None
            band = risk.band if risk else None
            unack = sum(1 for a in open_alerts if a.bed_id == bed.bed_id)
            dev = devices.get(s.device_id) if s else None
            rows.append(
                {
                    "bed_id": bed.bed_id,
                    "ward": bed.ward,
                    "subject_code": bed.subject_code or (s.subject_code if s else None),
                    "has_pam": bool(bed.has_pam),
                    "session_id": s.id if s else None,
                    "session_status": s.status if s else None,
                    "band": band,
                    "light": STATUS_LIGHT.get(band, "grey"),
                    "score": risk.score if risk else None,
                    "signal_coverage": (risk.data_quality or {}).get("signal_coverage")
                    if risk
                    else None,
                    "unacknowledged_alerts": unack,
                    "device_id": s.device_id if s else None,
                    "battery_pct": dev.battery_pct if dev else None,
                    "last_seen_at": dev.last_seen_at.isoformat() if dev and dev.last_seen_at else None,
                }
            )

    # Unacknowledged alerts first, then band, then bed number.
    rows.sort(key=lambda r: (-r["unacknowledged_alerts"], -BAND_RANK.get(r["band"], 0), r["bed_id"]))
    return rows


@router.get("/shift-summary")
def shift_summary(
    shift: str = Query("day", pattern="^(night|day|evening)$"),
    principal: Principal = Depends(current_principal),
):
    """Actions to carry out this shift, aggregated by bed."""
    since = datetime.now(UTC) - timedelta(days=1)
    with db_session() as db:
        alerts = db.scalars(
            select(AlertRow).where(
                AlertRow.status.in_(("open", "acknowledged")),
                AlertRow.created_at >= since,
            )
        ).all()
    by_bed: dict[str, dict] = {}
    for a in alerts:
        key = a.bed_id or a.subject_code
        entry = by_bed.setdefault(
            key,
            {
                "bed_id": a.bed_id,
                "subject_code": a.subject_code,
                "actions": [],
                "alerts": [],
            },
        )
        for action in a.recommended_actions or []:
            if action not in entry["actions"]:
                entry["actions"].append(action)
        entry["alerts"].append(
            {"id": a.id, "title": a.title, "severity": a.severity, "status": a.status}
        )
    start, end = SHIFTS[shift]
    return {
        "shift": shift,
        "window": f"{start:02d}:00-{end:02d}:00",
        "generated_at": datetime.now(UTC).isoformat(),
        "beds": sorted(by_bed.values(), key=lambda r: str(r["bed_id"])),
    }


@router.get("/system-health")
def system_health(principal: Principal = Depends(current_principal)):
    now = datetime.now(UTC)
    with db_session() as db:
        devices = db.scalars(select(Device)).all()
        sessions = db.scalars(
            select(SessionRow).where(SessionRow.started_at >= now - timedelta(days=7))
        ).all()
    total_gaps = sum(len(s.gaps or []) for s in sessions)
    return {
        "devices": [
            {
                "device_id": d.device_id,
                "bed_id": d.bed_id,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                "stale": _is_stale(aware(d.last_seen_at), now),
                "battery_pct": d.battery_pct,
                "storage_free_pct": d.storage_free_pct,
                "electrode_ok": d.electrode_ok,
            }
            for d in devices
        ],
        "sessions_last_7d": len(sessions),
        "sessions_failed": sum(1 for s in sessions if s.status == "failed"),
        "data_gaps": total_gaps,
    }


def _is_stale(last_seen: datetime | None, now: datetime) -> bool:
    return last_seen is None or (now - last_seen) > timedelta(hours=12)
