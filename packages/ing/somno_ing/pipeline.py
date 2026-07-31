"""Nightly analysis pipeline.

Runs after the session closes, never during it (PRD 2.1 R1: this is not an
active patient monitor, so nothing here is allowed to be on a real-time path).
Idempotent by construction - re-running a session replaces its derived results
wholesale and produces the same output for the same algorithm_version.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import yaml
from sqlalchemy import delete, select

from . import alerts as alerts_mod
from . import features as features_mod
from . import risk as risk_mod
from .db import (
    AlertRow,
    ArousalRow,
    NightlyRiskRow,
    PostureSegmentRow,
    SignalSummary,
    SleepEpochRow,
    Session as SessionRow,
    SwallowEventRow,
    aware,
    db_session,
)
from .detect import Derived, build_detector
from .detect.rule_based import DETECTOR_VERSION
from .ingest import SessionIngestor, summary_rows
from .settings import get_settings
from .storage import derived_key, load_arrays


def persist_ingest(ing: SessionIngestor) -> None:
    """Create or update the session row plus its PSG annotations and summaries."""
    ing.finish()
    with db_session() as db:
        row = db.get(SessionRow, ing.session_id)
        if row is None:
            row = SessionRow(id=ing.session_id, subject_code=ing.subject_code)
            db.add(row)
        row.subject_code = ing.subject_code
        row.device_id = ing.device_id
        row.bed_id = ing.bed_id
        row.scenario = ing.scenario
        row.seed = ing.seed
        row.duration_ms = ing.duration_ms or ing.derived.duration_ms
        row.sample_rates = ing.sample_rates
        row.gaps = ing.gaps
        row.chunks_received = ing.chunks_received
        row.status = "closed"
        row.ended_at = datetime.now(UTC)

        if ing.psg:
            db.execute(delete(SleepEpochRow).where(SleepEpochRow.session_id == ing.session_id))
            db.execute(delete(ArousalRow).where(ArousalRow.session_id == ing.session_id))
            for e in ing.psg.get("epochs", []):
                db.add(
                    SleepEpochRow(
                        session_id=ing.session_id,
                        t_start_ms=e["t_start_ms"],
                        stage=e["stage"],
                    )
                )
            for a in ing.psg.get("arousals", []):
                db.add(
                    ArousalRow(
                        id=a["id"],
                        session_id=ing.session_id,
                        t_start_ms=a["t_start_ms"],
                        duration_ms=a["duration_ms"],
                    )
                )

        db.execute(delete(SignalSummary).where(SignalSummary.session_id == ing.session_id))
        for r in summary_rows(ing.session_id, ing.derived):
            db.add(SignalSummary(**r))


def analyze(session_id: str) -> dict:
    """Detect, characterise, score, and raise alerts for one closed session."""
    settings = get_settings()
    with db_session() as db:
        session = db.get(SessionRow, session_id)
        if session is None:
            raise LookupError(f"unknown session {session_id}")
        subject_code = session.subject_code
        bed_id = session.bed_id
        scenario = session.scenario
        started_at = aware(session.started_at) or datetime.now(UTC)
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
        session.status = "analyzing"

    derived = Derived.from_dict(load_arrays(derived_key(session_id)))

    detector = build_detector()
    events = detector.finalize(derived)
    gating = detector.last_gating

    annotations = features_mod.annotate_events(events, derived, epochs, arousals)

    risk_cfg = risk_mod.RiskConfig()
    sfi_ref = _sfi_reference(settings.risk_config)
    feats = features_mod.compute(events, annotations, derived, arousals, sfi_reference_s=sfi_ref)

    coverage = float(derived.present.mean()) if len(derived) else 0.0
    quality = risk_mod.DataQuality(
        signal_coverage=coverage,
        artifact_ratio=gating.artifact_ratio if gating else 0.0,
    )
    risk = risk_mod.score(feats, quality, risk_cfg)

    with db_session() as db:
        repeats = _repeat_counts(db, subject_code, started_at)
    fired, summary = alerts_mod.evaluate(
        subject_code=subject_code,
        features=feats.to_dict(),
        risk=risk,
        repeat_counts=repeats,
    )

    with db_session() as db:
        db.execute(
            delete(SwallowEventRow).where(
                SwallowEventRow.session_id == session_id,
                SwallowEventRow.source == "detected",
            )
        )
        for ev, ann in zip(events, annotations):
            db.add(
                SwallowEventRow(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    t_start_ms=ev.t_start_ms,
                    t_end_ms=ev.t_end_ms,
                    confidence=ev.confidence,
                    source="detected",
                    modality_votes=ev.modality_votes,
                    sleep_stage=ann.sleep_stage,
                    arousal_linked=ann.arousal_linked,
                    arousal_id=ann.arousal_id,
                    resp_phase_before=ann.resp_phase_before,
                    resp_phase_after=ann.resp_phase_after,
                    coordination_pattern=ann.coordination_pattern,
                    swallow_apnea_ms=ann.swallow_apnea_ms,
                    posture=ann.posture,
                    hob_angle_deg=ann.hob_angle_deg,
                )
            )

        db.execute(
            delete(PostureSegmentRow).where(PostureSegmentRow.session_id == session_id)
        )
        for seg in features_mod.posture_segments(derived):
            db.add(PostureSegmentRow(session_id=session_id, source="detected", **seg))

        existing = db.get(NightlyRiskRow, session_id)
        if existing is not None:
            db.delete(existing)
            db.flush()
        db.add(
            NightlyRiskRow(
                session_id=session_id,
                score=risk["score"],
                band=risk["band"],
                components=risk["components"],
                data_quality=risk["data_quality"],
                features=feats.to_dict(),
                algorithm_version=risk["algorithm_version"],
            )
        )

        # Re-running an analysis supersedes its previous alerts rather than
        # deleting them: an alert somebody already acted on is part of the record.
        for old in db.scalars(
            select(AlertRow).where(AlertRow.session_id == session_id, AlertRow.status == "open")
        ):
            old.status = "superseded"

        for a in fired:
            body = a.body
            if summary and a is fired[0]:
                body = f"{body}\n\n{summary}".strip()
            db.add(
                AlertRow(
                    id=alerts_mod.new_alert_id(),
                    session_id=session_id,
                    subject_code=subject_code,
                    bed_id=bed_id,
                    rule_id=a.rule_id,
                    severity=a.severity,
                    status="open",
                    title=a.title,
                    body=body,
                    recommended_actions=a.recommended_actions,
                    dedup_key=a.dedup_key,
                    repeat_nights=a.repeat_nights,
                    deliver_after=a.deliver_after,
                    context=a.context,
                )
            )

        session = db.get(SessionRow, session_id)
        session.status = "analyzed"

    return {
        "session_id": session_id,
        "scenario": scenario,
        "detector_version": DETECTOR_VERSION,
        "n_events": len(events),
        "features": feats.to_dict(),
        "risk": risk,
        "alerts": [
            {
                "rule_id": a.rule_id,
                "severity": a.severity,
                "title": a.title,
                "recommended_actions": a.recommended_actions,
            }
            for a in fired
        ],
        "folded_summary": summary,
    }


def _sfi_reference(path) -> float:
    try:
        raw = yaml.safe_load(open(path).read()) or {}
        return float(raw.get("features", {}).get("sfi_reference_s", 600.0))
    except Exception:
        return 600.0


def _repeat_counts(db, subject_code: str, night: datetime) -> dict[str, int]:
    """Consecutive prior nights each dedup_key has fired, ending the night before."""
    rows = db.scalars(
        select(AlertRow).where(
            AlertRow.subject_code == subject_code,
            AlertRow.created_at >= night - timedelta(days=14),
        )
    ).all()
    by_key: dict[str, set] = {}
    for r in rows:
        created = aware(r.created_at)
        if created is None:
            continue
        by_key.setdefault(r.dedup_key, set()).add(created.date())

    out: dict[str, int] = {}
    base = night.date()
    for key, dates in by_key.items():
        count = 0
        cursor = base - timedelta(days=1)
        while cursor in dates:
            count += 1
            cursor -= timedelta(days=1)
        if count:
            out[key] = count
    return out
