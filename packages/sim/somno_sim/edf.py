"""EDF+ export (SIM-5.3).

Written record-by-record rather than all at once: at 16 kHz an eight-hour
acoustic channel alone is ~460 M samples, which is not something to hold in
memory just to prove PSG interoperability.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyedflib

from .physiology import EPOCH_MS, Night
from .signals import CHANNELS

RECORD_SEC = 1

# EDF stores int16, so each channel needs a physical range that covers it.
PHYSICAL_RANGE = {
    "acoustic": 1.0,
    "semg": 400.0,
    **{f"imu_{a}": 4.0 for a in ("ax", "ay", "az")},
    **{f"imu_{a}": 500.0 for a in ("gx", "gy", "gz")},
}
DIMENSION = {
    "acoustic": "a.u.",
    "semg": "uV",
    **{f"imu_{a}": "g" for a in ("ax", "ay", "az")},
    **{f"imu_{a}": "dps" for a in ("gx", "gy", "gz")},
}


class EdfExporter:
    """Accepts the same chunks as the publisher and streams them into an EDF+ file."""

    def __init__(self, path: Path, fs: dict[str, float], subject_code: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.fs = fs
        self.writer = pyedflib.EdfWriter(
            str(path), len(CHANNELS), file_type=pyedflib.FILETYPE_EDFPLUS
        )
        self.writer.setPatientCode(subject_code)
        self.writer.setEquipment("SomnoSwallow-SIM")
        # One-second data records, which is pyedflib's default; setting it
        # explicitly changes the sample frequencies it computes on read-back.
        self.writer.setSignalHeaders(
            [
                pyedflib.highlevel.make_signal_header(
                    label=name,
                    dimension=DIMENSION[name],
                    sample_frequency=fs[name],
                    physical_min=-PHYSICAL_RANGE[name],
                    physical_max=PHYSICAL_RANGE[name],
                )
                for name in CHANNELS
            ]
        )
        self._buf: dict[str, np.ndarray] = {c: np.zeros(0) for c in CHANNELS}

    def add(self, channels: dict[str, np.ndarray]) -> None:
        for name in CHANNELS:
            self._buf[name] = np.concatenate([self._buf[name], channels[name]])
        self._flush()

    def _flush(self, final: bool = False) -> None:
        while True:
            need = {c: int(self.fs[c] * RECORD_SEC) for c in CHANNELS}
            if not all(len(self._buf[c]) >= need[c] for c in CHANNELS):
                break
            record = []
            for c in CHANNELS:
                seg = np.clip(
                    self._buf[c][: need[c]], -PHYSICAL_RANGE[c], PHYSICAL_RANGE[c] * 0.999
                )
                record.append(seg)
                self._buf[c] = self._buf[c][need[c] :]
            self.writer.blockWritePhysicalSamples(np.concatenate(record))

    def annotate(self, night: Night) -> None:
        for sw in night.swallows:
            self.writer.writeAnnotation(
                sw.t_start_ms / 1000.0,
                (sw.t_end_ms - sw.t_start_ms) / 1000.0,
                f"swallow {sw.coordination_pattern}",
            )
        for a in night.arousals:
            self.writer.writeAnnotation(a.t_start_ms / 1000.0, a.duration_ms / 1000.0, "arousal")
        prev = None
        for i, stage in enumerate(night.hypnogram):
            if stage != prev:
                self.writer.writeAnnotation(i * EPOCH_MS / 1000.0, -1, f"stage {stage}")
                prev = stage

    def close(self) -> None:
        self.writer.close()
