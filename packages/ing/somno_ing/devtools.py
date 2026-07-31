"""Development harness: run SIM through the real ingest path, in process.

Used by the detector's own test suite and by ``somno-ing simulate``. It exercises
the same ``SessionIngestor`` and the same ``analyze`` the MQTT consumer uses -
the only thing swapped out is the transport.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete, select

from .db import SwallowEventRow, db_session, init_db
from .detect.rule_based import DETECTOR_VERSION
from .eval import report
from .ingest import SessionIngestor
from .ingest.consumer import IngestService
from .pipeline import analyze, persist_ingest


def run_scenario(
    scenario: str = "healthy_adult",
    seed: int = 42,
    duration_min: float | None = None,
    subject_code: str = "SUBJ-001",
    bed_id: str | None = "BED-01",
    device_id: str = "dev-001",
    analyze_after: bool = True,
) -> dict:
    """Generate a night with SIM, feed it through ingest, and analyse it."""
    from somno_sim.config import load_scenario
    from somno_sim.groundtruth import swallow_events
    from somno_sim.physiology import build_night
    from somno_sim.publisher import CallbackPublisher
    from somno_sim.runner import run

    init_db()
    cfg = load_scenario(scenario)
    if duration_min is not None:
        cfg = cfg.model_copy(update={"duration_min": duration_min})

    service = IngestService(on_session_closed=lambda ing: None)
    closed: list[SessionIngestor] = []

    def on_closed(ing: SessionIngestor) -> None:
        closed.append(ing)

    service.on_session_closed = on_closed
    publisher = CallbackPublisher(lambda topic, payload: service.handle(topic, payload))

    result = run(
        cfg,
        seed=seed,
        device_id=device_id,
        publisher=publisher,
        out_dir=None,
        speed=0.0,
        subject_code=subject_code,
        bed_id=bed_id,
    )

    if not closed:
        raise RuntimeError("session never closed - SIM did not emit session_end")
    ing = closed[0]
    persist_ingest(ing)

    # Ground truth is stored alongside the detected events so /v1/eval/detection
    # can score without SIM being reachable at request time.
    night = build_night(cfg, seed)
    gt = swallow_events(result.session_id, night)
    with db_session() as db:
        # Idempotent: re-running the same scenario+seed replaces its ground truth.
        db.execute(
            delete(SwallowEventRow).where(
                SwallowEventRow.session_id == result.session_id,
                SwallowEventRow.source == "ground_truth",
            )
        )
        for e in gt:
            db.add(
                SwallowEventRow(
                    id=e.id,
                    session_id=result.session_id,
                    t_start_ms=e.t_start_ms,
                    t_end_ms=e.t_end_ms,
                    confidence=1.0,
                    source="ground_truth",
                    sleep_stage=str(e.sleep_stage.value if e.sleep_stage else "UNKNOWN"),
                    arousal_linked=bool(e.arousal_linked),
                    arousal_id=e.arousal_id,
                    resp_phase_before=str(e.resp_phase_before.value),
                    resp_phase_after=str(e.resp_phase_after.value),
                    coordination_pattern=str(e.coordination_pattern.value),
                    swallow_apnea_ms=e.swallow_apnea_ms,
                    posture=str(e.posture.value),
                    hob_angle_deg=e.hob_angle_deg,
                )
            )

    out = {"session_id": result.session_id, "scenario": cfg.scenario, "seed": seed}
    if analyze_after:
        out["analysis"] = analyze(result.session_id)
        out["eval"] = evaluate_session(result.session_id)
    return out


def evaluate_session(session_id: str, tolerance_ms: int = 750) -> dict:
    with db_session() as db:
        rows = db.scalars(
            select(SwallowEventRow).where(SwallowEventRow.session_id == session_id)
        ).all()
        from .db import Session as SessionRow

        session = db.get(SessionRow, session_id)
        scenario = session.scenario if session else None
        gt = [_row_dict(r) for r in rows if r.source == "ground_truth"]
        det = [_row_dict(r) for r in rows if r.source == "detected"]
    gt.sort(key=lambda e: e["t_start_ms"])
    det.sort(key=lambda e: e["t_start_ms"])
    return report(
        session_id, gt, det, tolerance_ms, scenario=scenario, detector_version=DETECTOR_VERSION
    )


def _row_dict(r: SwallowEventRow) -> dict:
    return {
        "t_start_ms": r.t_start_ms,
        "t_end_ms": r.t_end_ms,
        "sleep_stage": r.sleep_stage,
        "coordination_pattern": r.coordination_pattern,
        "confidence": r.confidence,
    }


def write_report(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
