"""EDF+ export of a stored session (PRD 6.6).

Exports the 100 Hz derived series plus the event annotations rather than the
raw waveform, because raw retention is opt-in. When raw chunks were kept, they
are exported at full rate instead.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pyedflib
from sqlalchemy import select

from ..db import ArousalRow, SleepEpochRow, SwallowEventRow, db_session
from ..detect import Derived
from ..storage import derived_key, load_arrays

DERIVED_CHANNELS = (
    ("acoustic_env", "a.u.", 1.0),
    ("snore_env", "a.u.", 1.0),
    ("semg_env", "uV", 400.0),
    ("imu_si", "g", 4.0),
    ("resp_volume", "g", 1.0),
)


def export_session(session_id: str) -> bytes:
    try:
        d = Derived.from_dict(load_arrays(derived_key(session_id)))
    except Exception as exc:
        raise FileNotFoundError(f"no derived signal stored for {session_id}") from exc

    with db_session() as db:
        events = db.scalars(
            select(SwallowEventRow).where(
                SwallowEventRow.session_id == session_id,
                SwallowEventRow.source == "detected",
            )
        ).all()
        arousals = db.scalars(
            select(ArousalRow).where(ArousalRow.session_id == session_id)
        ).all()
        epochs = db.scalars(
            select(SleepEpochRow)
            .where(SleepEpochRow.session_id == session_id)
            .order_by(SleepEpochRow.t_start_ms)
        ).all()
        marks = [(e.t_start_ms, e.t_end_ms, e.coordination_pattern) for e in events]
        arousal_marks = [(a.t_start_ms, a.duration_ms) for a in arousals]
        stage_marks = [(e.t_start_ms, e.stage) for e in epochs]

    fs = int(d.fs)
    n_records = len(d) // fs
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{session_id}.edf"
        writer = pyedflib.EdfWriter(str(path), len(DERIVED_CHANNELS), file_type=pyedflib.FILETYPE_EDFPLUS)
        writer.setPatientCode(session_id)
        writer.setEquipment("SomnoSwallow-ING-derived")
        writer.setSignalHeaders(
            [
                pyedflib.highlevel.make_signal_header(
                    label=name, dimension=unit, sample_frequency=fs,
                    physical_min=-rng, physical_max=rng,
                )
                for name, unit, rng in DERIVED_CHANNELS
            ]
        )
        for i in range(n_records):
            block = []
            for name, _unit, rng in DERIVED_CHANNELS:
                seg = np.asarray(getattr(d, name)[i * fs : (i + 1) * fs], dtype=np.float64)
                block.append(np.clip(seg, -rng, rng * 0.999))
            writer.blockWritePhysicalSamples(np.concatenate(block))

        for t0, t1, pattern in marks:
            writer.writeAnnotation(t0 / 1000.0, (t1 - t0) / 1000.0, f"swallow {pattern}")
        for t0, dur in arousal_marks:
            writer.writeAnnotation(t0 / 1000.0, dur / 1000.0, "arousal")
        prev = None
        for t0, stage in stage_marks:
            if stage != prev:
                writer.writeAnnotation(t0 / 1000.0, -1, f"stage {stage}")
                prev = stage
        writer.close()
        return path.read_bytes()
