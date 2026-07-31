"""Session, event, risk, timeline and trend endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select

from ..db import (
    ArousalRow,
    NightlyRiskRow,
    PostureSegmentRow,
    SignalSummary,
    SleepEpochRow,
    Session as SessionRow,
    SwallowEventRow,
    db_session,
)
from ..detect import Derived
from ..storage import derived_key, load_arrays
from .deps import Principal, current_principal, require

router = APIRouter(prefix="/v1", tags=["sessions"])


class CreateSession(BaseModel):
    session_id: str | None = None
    subject_code: str
    device_id: str
    bed_id: str | None = None
    scenario: str | None = None
    seed: int | None = None
    duration_ms: int | None = None


@router.post("/sessions", status_code=201)
def create_session(body: CreateSession, principal: Principal = Depends(require("researcher", "nurse"))):
    import uuid

    sid = body.session_id or str(uuid.uuid4())
    with db_session() as db:
        if db.get(SessionRow, sid) is not None:
            raise HTTPException(409, "session already exists")
        db.add(
            SessionRow(
                id=sid,
                subject_code=body.subject_code,
                device_id=body.device_id,
                bed_id=body.bed_id,
                scenario=body.scenario,
                seed=body.seed,
                duration_ms=body.duration_ms,
                status="recording",
                started_at=datetime.now(UTC),
            )
        )
    return {"id": sid, "status": "recording"}


@router.post("/sessions/{session_id}/upload")
async def upload_session(
    session_id: str,
    file: UploadFile,
    principal: Principal = Depends(require("researcher", "nurse")),
):
    """Offline import - the microSD path (ING-3).

    Accepts the same newline-delimited chunk envelopes the device publishes, so
    an offline recording and a streamed one go through identical processing.
    """
    from ..ingest.consumer import IngestService
    from ..pipeline import persist_ingest
    from ..tasks import analyze_session

    service = IngestService(on_session_closed=lambda ing: None)
    closed = []
    service.on_session_closed = closed.append

    count = 0
    for line in (await file.read()).decode().splitlines():
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        service.handle(msg["topic"], msg["payload"])
        count += 1

    if not closed:
        ing = service.sessions.pop(session_id, None)
        if ing is None:
            raise HTTPException(400, "upload contained no chunks for this session")
        closed.append(ing)

    persist_ingest(closed[0])
    analyze_session.delay(closed[0].session_id)
    return {"session_id": closed[0].session_id, "messages": count, "status": "analyzing"}


@router.post("/sessions/{session_id}/close")
def close_session(session_id: str, principal: Principal = Depends(require("researcher", "nurse"))):
    from ..tasks import analyze_session

    with db_session() as db:
        row = db.get(SessionRow, session_id)
        if row is None:
            raise HTTPException(404, "unknown session")
        row.status = "closed"
        row.ended_at = datetime.now(UTC)
    analyze_session.delay(session_id)
    return {"session_id": session_id, "status": "analyzing"}


@router.get("/sessions")
def list_sessions(
    subject_code: str | None = None,
    limit: int = Query(50, le=500),
    principal: Principal = Depends(current_principal),
):
    with db_session() as db:
        q = select(SessionRow).order_by(SessionRow.started_at.desc()).limit(limit)
        if subject_code:
            q = q.where(SessionRow.subject_code == subject_code)
        return [_session_dict(r) for r in db.scalars(q)]


@router.get("/sessions/{session_id}")
def get_session(session_id: str, principal: Principal = Depends(current_principal)):
    with db_session() as db:
        row = db.get(SessionRow, session_id)
        if row is None:
            raise HTTPException(404, "unknown session")
        risk = db.get(NightlyRiskRow, session_id)
        n_events = db.scalar(
            select(func.count())
            .select_from(SwallowEventRow)
            .where(
                SwallowEventRow.session_id == session_id,
                SwallowEventRow.source == "detected",
            )
        )
        out = _session_dict(row)
        out["n_events"] = int(n_events or 0)
        out["risk"] = _risk_dict(risk) if risk else None
        return out


@router.get("/sessions/{session_id}/events")
def list_events(
    session_id: str,
    source: str = "detected",
    min_confidence: float = 0.0,
    coordination_pattern: str | None = None,
    offset: int = 0,
    limit: int = Query(200, le=2000),
    principal: Principal = Depends(current_principal),
):
    with db_session() as db:
        q = (
            select(SwallowEventRow)
            .where(
                SwallowEventRow.session_id == session_id,
                SwallowEventRow.source == source,
                SwallowEventRow.confidence >= min_confidence,
            )
            .order_by(SwallowEventRow.t_start_ms)
        )
        if coordination_pattern:
            q = q.where(SwallowEventRow.coordination_pattern == coordination_pattern)
        total = db.scalar(select(func.count()).select_from(q.subquery()))
        rows = db.scalars(q.offset(offset).limit(limit)).all()
        return {
            "total": int(total or 0),
            "offset": offset,
            "limit": limit,
            "items": [_event_dict(r) for r in rows],
        }


@router.get("/sessions/{session_id}/risk")
def get_risk(session_id: str, principal: Principal = Depends(current_principal)):
    with db_session() as db:
        row = db.get(NightlyRiskRow, session_id)
        if row is None:
            raise HTTPException(404, "no analysis for this session yet")
        return _risk_dict(row)


@router.get("/sessions/{session_id}/timeline")
def get_timeline(
    session_id: str,
    points: int = Query(1200, le=5000),
    principal: Principal = Depends(current_principal),
):
    """Downsampled whole-night view: stages, events, posture, signal envelope.

    Downsampling happens here rather than in the browser so the 8-hour chart
    stays inside the PRD's 500 ms render budget regardless of session length.
    """
    with db_session() as db:
        session = db.get(SessionRow, session_id)
        if session is None:
            raise HTTPException(404, "unknown session")
        epochs = [
            {"t_start_ms": r.t_start_ms, "stage": r.stage}
            for r in db.scalars(
                select(SleepEpochRow)
                .where(SleepEpochRow.session_id == session_id)
                .order_by(SleepEpochRow.t_start_ms)
            )
        ]
        arousals = [
            {"id": r.id, "t_start_ms": r.t_start_ms, "duration_ms": r.duration_ms}
            for r in db.scalars(select(ArousalRow).where(ArousalRow.session_id == session_id))
        ]
        postures = [
            {
                "t_start_ms": r.t_start_ms,
                "t_end_ms": r.t_end_ms,
                "posture": r.posture,
                "hob_angle_deg": r.hob_angle_deg,
            }
            for r in db.scalars(
                select(PostureSegmentRow)
                .where(PostureSegmentRow.session_id == session_id)
                .order_by(PostureSegmentRow.t_start_ms)
            )
        ]
        events = [
            _event_dict(r)
            for r in db.scalars(
                select(SwallowEventRow)
                .where(
                    SwallowEventRow.session_id == session_id,
                    SwallowEventRow.source == "detected",
                )
                .order_by(SwallowEventRow.t_start_ms)
            )
        ]
        summary = db.scalars(
            select(SignalSummary)
            .where(SignalSummary.session_id == session_id)
            .order_by(SignalSummary.t_ms)
        ).all()

    signal = _downsample_summary(summary, points)
    return {
        "session_id": session_id,
        "duration_ms": session.duration_ms,
        "epochs": epochs,
        "arousals": arousals,
        "postures": postures,
        "events": events,
        "signal": signal,
    }


@router.get("/sessions/{session_id}/signal")
def get_signal_window(
    session_id: str,
    t_start_ms: int = 0,
    t_end_ms: int = 60_000,
    principal: Principal = Depends(require("researcher", "nurse")),
):
    """Derived waveform window for the research signal viewer (STATION S-3)."""
    if t_end_ms - t_start_ms > 300_000:
        raise HTTPException(400, "window may not exceed 5 minutes")
    try:
        d = Derived.from_dict(load_arrays(derived_key(session_id)))
    except Exception:
        raise HTTPException(404, "no derived signal stored for this session") from None
    a, b = d.index(t_start_ms), d.index(t_end_ms)
    step = max(1, (b - a) // 4000)
    return {
        "session_id": session_id,
        "fs_hz": d.fs / step,
        "t_start_ms": t_start_ms,
        "acoustic_env": d.acoustic_env[a:b:step].tolist(),
        "semg_env": d.semg_env[a:b:step].tolist(),
        "imu_si": d.imu_si[a:b:step].tolist(),
        "resp_volume": d.resp_volume[a:b:step].tolist(),
        "gated": d.gated[a:b:step].astype(int).tolist(),
    }


@router.get("/sessions/{session_id}/export/edf")
def export_edf(session_id: str, principal: Principal = Depends(require("researcher"))):
    from ..export.edf import export_session

    try:
        data = export_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from None
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{session_id}.edf"'},
    )


@router.get("/subjects/{subject_code}/trend")
def get_trend(
    subject_code: str,
    nights: int = Query(30, le=180),
    principal: Principal = Depends(current_principal),
):
    from ..db import CareActionRow

    since = datetime.now(UTC) - timedelta(days=nights)
    with db_session() as db:
        sessions = db.scalars(
            select(SessionRow)
            .where(SessionRow.subject_code == subject_code, SessionRow.started_at >= since)
            .order_by(SessionRow.started_at)
        ).all()
        out = []
        for s in sessions:
            risk = db.get(NightlyRiskRow, s.id)
            feats = (risk.features or {}) if risk else {}
            out.append(
                {
                    "session_id": s.id,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "band": risk.band if risk else None,
                    "score": risk.score if risk else None,
                    "n_events": feats.get("n_events"),
                    "sfi_max_s": feats.get("sfi_max_s"),
                    "supine_burden": feats.get("supine_burden"),
                    "coordination_anomaly": feats.get("coordination_anomaly"),
                }
            )
        actions = [
            {
                "action": a.action,
                "performed_at": a.performed_at.isoformat() if a.performed_at else None,
                "performed_by": a.performed_by,
            }
            for a in db.scalars(
                select(CareActionRow)
                .where(
                    CareActionRow.subject_code == subject_code,
                    CareActionRow.performed_at >= since,
                )
                .order_by(CareActionRow.performed_at)
            )
        ]
    return {"subject_code": subject_code, "nights": out, "care_actions": actions}


# ------------------------------------------------------------------ helpers
def _session_dict(r: SessionRow) -> dict:
    return {
        "id": r.id,
        "subject_code": r.subject_code,
        "device_id": r.device_id,
        "bed_id": r.bed_id,
        "status": r.status,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "ended_at": r.ended_at.isoformat() if r.ended_at else None,
        "duration_ms": r.duration_ms,
        "scenario": r.scenario,
        "seed": r.seed,
        "gaps": r.gaps or [],
        "sample_rates": r.sample_rates or {},
    }


def _event_dict(r: SwallowEventRow) -> dict:
    return {
        "id": r.id,
        "session_id": r.session_id,
        "t_start_ms": r.t_start_ms,
        "t_end_ms": r.t_end_ms,
        "confidence": r.confidence,
        "source": r.source,
        "modality_votes": r.modality_votes or {},
        "sleep_stage": r.sleep_stage,
        "arousal_linked": r.arousal_linked,
        "arousal_id": r.arousal_id,
        "resp_phase_before": r.resp_phase_before,
        "resp_phase_after": r.resp_phase_after,
        "coordination_pattern": r.coordination_pattern,
        "swallow_apnea_ms": r.swallow_apnea_ms,
        "posture": r.posture,
        "hob_angle_deg": r.hob_angle_deg,
    }


def _risk_dict(r: NightlyRiskRow) -> dict:
    return {
        "session_id": r.session_id,
        "score": r.score,
        "band": r.band,
        "components": r.components or {},
        "data_quality": r.data_quality or {},
        "features": r.features or {},
        "algorithm_version": r.algorithm_version,
        "computed_at": r.computed_at.isoformat() if r.computed_at else None,
    }


def _downsample_summary(rows: list[SignalSummary], points: int) -> list[dict]:
    if not rows:
        return []
    step = max(1, len(rows) // max(points, 1))
    out = []
    for i in range(0, len(rows), step):
        block = rows[i : i + step]
        out.append(
            {
                "t_ms": block[0].t_ms,
                "acoustic": round(float(np.mean([b.acoustic_swallow_band or 0 for b in block])), 6),
                "semg": round(float(np.mean([b.semg_rms or 0 for b in block])), 4),
                "resp": round(float(np.mean([b.resp_volume or 0 for b in block])), 6),
                "artifact": any(b.artifact for b in block),
                "snoring": any(b.snoring for b in block),
                "coverage": round(float(np.mean([b.coverage or 0 for b in block])), 3),
            }
        )
    return out
