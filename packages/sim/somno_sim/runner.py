"""Run orchestration: build the night, render it, publish it, write the truth."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

import numpy as np

from . import groundtruth
from .config import Scenario
from .physiology import build_night
from .publisher import CONTROL_TOPIC, SIGNAL_TOPIC, Publisher, encode_chunk
from .signals import CHANNELS, Synthesizer

# Fixed namespace so the same scenario+seed+device always names the same session.
SESSION_NS = uuid.UUID("6f3f8f5c-1c9d-5a1e-9a0d-7f2c4b8e11aa")


@dataclass
class RunResult:
    session_id: str
    scenario: str
    seed: int
    duration_ms: int
    n_chunks: int
    n_swallows: int
    ground_truth_path: Path | None
    edf_path: Path | None
    wall_seconds: float


def session_id_for(scenario: str, seed: int, device_id: str) -> str:
    return str(uuid.uuid5(SESSION_NS, f"{scenario}:{seed}:{device_id}"))


def run(
    cfg: Scenario,
    seed: int,
    device_id: str,
    publisher: Publisher,
    out_dir: Path | None = None,
    speed: float = 60.0,
    subject_code: str = "SUBJ-001",
    bed_id: str | None = None,
    export_edf: bool = False,
    save_raw: bool = False,
    progress: Callable[[int, int], None] | None = None,
) -> RunResult:
    """Render one night.

    ``speed`` is a wall-clock pacing factor: 1 is real time, 60 is sixty times
    faster, 0 means no pacing at all (generate as fast as the machine allows).
    """
    started = time.monotonic()
    night = build_night(cfg, seed)
    synth = Synthesizer(cfg, night, seed)
    session_id = session_id_for(cfg.scenario, seed, device_id)

    s = cfg.signal
    fs = {
        "acoustic": s.acoustic_fs_hz,
        "semg": s.semg_fs_hz,
        **{f"imu_{a}": s.imu_fs_hz for a in ("ax", "ay", "az", "gx", "gy", "gz")},
    }
    n_chunks = int(np.ceil(cfg.duration_ms / s.chunk_ms))

    exporter = None
    if export_edf and out_dir is not None:
        from .edf import EdfExporter

        exporter = EdfExporter(out_dir / "session.edf", fs, subject_code)

    raw_fh = None
    if save_raw and out_dir is not None:
        (out_dir / "raw").mkdir(parents=True, exist_ok=True)

    publisher.publish(
        CONTROL_TOPIC.format(device_id=device_id),
        {
            "event": "session_start",
            "session_id": session_id,
            "device_id": device_id,
            "subject_code": subject_code,
            "bed_id": bed_id,
            "scenario": cfg.scenario,
            "seed": seed,
            "started_at": datetime.now(UTC).isoformat(),
            "duration_ms": cfg.duration_ms,
            "sample_rates": {
                "acoustic_hz": s.acoustic_fs_hz,
                "imu_hz": s.imu_fs_hz,
                "semg_hz": s.semg_fs_hz,
            },
            "psg": groundtruth.psg_annotations(session_id, night).model_dump(
                mode="json", exclude_none=True
            ),
        },
    )

    topic = SIGNAL_TOPIC.format(device_id=device_id)
    wall_start = time.monotonic()
    for seq in range(n_chunks):
        t0 = seq * s.chunk_ms
        t1 = min(t0 + s.chunk_ms, cfg.duration_ms)
        data = synth.render(seq, t0, t1)

        payload = encode_chunk(
            device_id=device_id,
            session_id=session_id,
            seq=seq,
            t_start_ms=t0,
            duration_ms=t1 - t0,
            channels={c: data[c] for c in CHANNELS},
            fs=fs,
            device_state={
                "battery_pct": round(max(5.0, 100.0 - 90.0 * (t1 / max(1, cfg.duration_ms))), 1),
                "electrode_ok": synth.artifacts.electrode_ok(t0),
                "storage_free_pct": round(max(1.0, 95.0 - 60.0 * (t1 / max(1, cfg.duration_ms))), 1),
            },
        )
        publisher.publish(topic, payload)

        if exporter is not None:
            exporter.add(data)
        if save_raw and out_dir is not None:
            np.savez_compressed(out_dir / "raw" / f"chunk_{seq:06d}.npz", **data)
        if progress is not None:
            progress(seq + 1, n_chunks)

        if speed > 0:
            target = wall_start + (t1 / 1000.0) / speed
            delay = target - time.monotonic()
            if delay > 0:
                time.sleep(delay)

    publisher.publish(
        CONTROL_TOPIC.format(device_id=device_id),
        {
            "event": "session_end",
            "session_id": session_id,
            "device_id": device_id,
            "duration_ms": cfg.duration_ms,
            "n_chunks": n_chunks,
        },
    )

    gt_path = None
    if out_dir is not None:
        meta = {
            "scenario": cfg.scenario,
            "seed": seed,
            "device_id": device_id,
            "subject_code": subject_code,
            "bed_id": bed_id,
            "duration_ms": cfg.duration_ms,
            "sample_rates": {
                "acoustic_hz": s.acoustic_fs_hz,
                "imu_hz": s.imu_fs_hz,
                "semg_hz": s.semg_fs_hz,
            },
        }
        gt_path = groundtruth.write(out_dir, session_id, meta, night)
        (out_dir / "scenario.resolved.yaml").write_text(
            json.dumps(cfg.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        )

    if exporter is not None:
        exporter.annotate(night)
        exporter.close()
    if raw_fh is not None:
        raw_fh.close()

    return RunResult(
        session_id=session_id,
        scenario=cfg.scenario,
        seed=seed,
        duration_ms=cfg.duration_ms,
        n_chunks=n_chunks,
        n_swallows=len(night.swallows),
        ground_truth_path=gt_path,
        edf_path=(out_dir / "session.edf") if exporter is not None else None,
        wall_seconds=time.monotonic() - started,
    )
