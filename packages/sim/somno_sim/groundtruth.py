"""Ground truth serialisation (SIM-5.2).

This file is the reason SIM exists. Detection quality is only meaningful
relative to a known answer, so every run writes the exact event list that was
rendered into the waveform.
"""

from __future__ import annotations

import json
from pathlib import Path

from somno_schemas import (
    ArousalEvent,
    EventSource,
    PostureSegment,
    PsgAnnotations,
    SleepEpoch,
    SwallowEvent,
)

from .physiology import EPOCH_MS, Night


def swallow_events(session_id: str, night: Night) -> list[SwallowEvent]:
    return [
        SwallowEvent(
            id=sw.id,
            session_id=session_id,
            t_start_ms=sw.t_start_ms,
            t_end_ms=sw.t_end_ms,
            confidence=1.0,
            source=EventSource.GROUND_TRUTH,
            sleep_stage=sw.sleep_stage,
            arousal_linked=sw.arousal_linked,
            arousal_id=sw.arousal_id,
            resp_phase_before=sw.resp_phase_before,
            resp_phase_after=sw.resp_phase_after,
            coordination_pattern=sw.coordination_pattern,
            swallow_apnea_ms=sw.swallow_apnea_ms,
            posture=sw.posture,
            hob_angle_deg=sw.hob_angle_deg,
        )
        for sw in night.swallows
    ]


def psg_annotations(session_id: str, night: Night) -> PsgAnnotations:
    return PsgAnnotations(
        session_id=session_id,
        epoch_sec=EPOCH_MS // 1000,
        epochs=[
            SleepEpoch(t_start_ms=i * EPOCH_MS, stage=s) for i, s in enumerate(night.hypnogram)
        ],
        arousals=[
            ArousalEvent(id=a.id, t_start_ms=a.t_start_ms, duration_ms=a.duration_ms)
            for a in night.arousals
        ],
        postures=[
            PostureSegment(
                t_start_ms=p.t_start_ms,
                t_end_ms=p.t_end_ms,
                posture=p.posture,
                hob_angle_deg=p.hob_angle_deg,
            )
            for p in night.postures
        ],
    )


def write(out_dir: Path, session_id: str, meta: dict, night: Night) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        **meta,
        "session_id": session_id,
        "swallow_events": [e.model_dump(mode="json", exclude_none=True) for e in swallow_events(session_id, night)],
        "psg": psg_annotations(session_id, night).model_dump(mode="json", exclude_none=True),
    }
    path = out_dir / "ground_truth.json"
    # sort_keys + fixed separators so the file hashes identically across runs.
    path.write_text(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return path
