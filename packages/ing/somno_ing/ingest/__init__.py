"""Ingest (PRD 6.1).

Stage 1 of detection runs *here*, as chunks arrive, and only the 100 Hz derived
series is retained. Keeping raw waveform is opt-in (``STORE_RAW``) because an
eight-hour night is roughly 1.4 GB on the wire and there is nothing downstream
that needs it except the research signal viewer and EDF export.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field

import numpy as np

from ..detect import DERIVED_FS, Derived, build_detector
from ..detect.preprocess import finalize_resp
from ..settings import get_settings
from ..storage import derived_key, raw_key, save_arrays

CHANNELS = ("acoustic", "imu_ax", "imu_ay", "imu_az", "imu_gx", "imu_gy", "imu_gz", "semg")


def decode_channels(payload: dict) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    data: dict[str, np.ndarray] = {}
    fs: dict[str, float] = {}
    for name, ch in payload["channels"].items():
        raw = np.frombuffer(base64.b64decode(ch["data_b64"]), dtype="<i2")
        data[name] = raw.astype(np.float64) * ch["scale"]
        fs[name] = float(ch["fs_hz"])
    return data, fs


@dataclass
class SessionIngestor:
    """Accumulates one session's derived series and tracks delivery gaps."""

    session_id: str
    device_id: str
    subject_code: str = "SUBJ-UNKNOWN"
    bed_id: str | None = None
    scenario: str | None = None
    seed: int | None = None
    duration_ms: int | None = None
    sample_rates: dict = field(default_factory=dict)
    psg: dict | None = None

    derived: Derived = field(default_factory=Derived)
    gaps: list[dict] = field(default_factory=list)
    chunks_received: int = 0
    next_seq: int = 0
    chunk_ms: int | None = None
    device_state: dict = field(default_factory=dict)
    _detector: object | None = None

    def on_chunk(self, payload: dict) -> None:
        channels, fs = decode_channels(payload)
        if self._detector is None:
            self._detector = build_detector(fs)
        self.chunk_ms = payload["duration_ms"]

        seq = int(payload["seq"])
        if seq < self.next_seq:
            return  # duplicate redelivery; MQTT QoS 1 is at-least-once
        if seq > self.next_seq:
            self._record_gap(self.next_seq, seq - 1, payload["t_start_ms"])

        state = payload.get("device_state") or {}
        self.device_state = state
        seg = self._detector.process_chunk(
            seq,
            payload["t_start_ms"],
            channels,
            fs,
            electrode_ok=bool(state.get("electrode_ok", True)),
        )
        # Align to absolute time: pad anything the gap left behind.
        self.derived.pad_to(int(payload["t_start_ms"] / 1000.0 * DERIVED_FS))
        self.derived.extend(seg)

        if get_settings().store_raw:
            save_arrays(raw_key(self.session_id, seq), **channels)

        self.chunks_received += 1
        self.next_seq = seq + 1

    def _record_gap(self, from_seq: int, to_seq: int, t_end_ms: int) -> None:
        span = self.chunk_ms or 0
        self.gaps.append(
            {
                "from_seq": from_seq,
                "to_seq": to_seq,
                "t_start_ms": int(t_end_ms - (to_seq - from_seq + 1) * span) if span else None,
                "t_end_ms": int(t_end_ms) if span else None,
            }
        )

    def finish(self) -> str:
        """Pad to the declared duration and persist the derived series."""
        if self.duration_ms:
            self.derived.pad_to(int(self.duration_ms / 1000.0 * DERIVED_FS))
        finalize_resp(self.derived)
        key = derived_key(self.session_id)
        save_arrays(key, **self.derived.to_dict())
        return key

    @property
    def signal_coverage(self) -> float:
        n = len(self.derived)
        return float(self.derived.present.mean()) if n else 0.0


def summary_rows(session_id: str, d: Derived, postures: list[dict] | None = None) -> list[dict]:
    """One row per second for the Timescale hypertable (PRD 6.1)."""
    if len(d) == 0:
        return []
    per = int(d.fs)
    n = len(d) // per
    if n == 0:
        return []

    def block(arr: np.ndarray, fn) -> np.ndarray:
        return fn(arr[: n * per].reshape(n, per), axis=1)

    from ..features import posture_series

    labels, hob = posture_series(d)
    rows = []
    ac = block(d.acoustic_env.astype(np.float64), np.mean)
    sn = block(d.snore_env.astype(np.float64), np.mean)
    eg = block(d.semg_env.astype(np.float64), np.mean)
    si = block(np.abs(d.imu_si.astype(np.float64)), np.mean)
    rv = block(d.resp_volume.astype(np.float64), np.mean)
    gated = block(d.gated.astype(np.float64), np.mean)
    snoring = block(d.snoring.astype(np.float64), np.mean)
    present = block(d.present.astype(np.float64), np.mean)
    lab = labels[: n * per : per]
    hb = hob[: n * per : per]

    for i in range(n):
        rows.append(
            {
                "session_id": session_id,
                "t_ms": i * 1000,
                "acoustic_rms": float(ac[i]),
                "acoustic_swallow_band": float(ac[i]),
                "acoustic_snore_band": float(sn[i]),
                "semg_rms": float(eg[i]),
                "imu_si_energy": float(si[i]),
                "resp_volume": float(rv[i]),
                "posture": str(lab[i]),
                "hob_angle_deg": float(hb[i]),
                "artifact": bool(gated[i] > 0.5),
                "snoring": bool(snoring[i] > 0.5),
                "coverage": float(present[i]),
            }
        )
    return rows
