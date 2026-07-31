"""Detection interfaces.

``SwallowDetector`` is the seam the PRD asks for: v1 ships ``RuleBasedDetector``,
and a future ``MLDetector`` implements the same two methods. Everything upstream
(ingest) and downstream (features, risk, alerts) talks only to this interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np

# All derived series are resampled to this rate. 100 Hz is the native IMU rate
# and is fast enough to time a swallow to ~10 ms, which is well inside the
# +/-300 ms fusion tolerance.
DERIVED_FS = 100.0

MODALITIES = ("acoustic", "imu", "semg")


@dataclass
class Candidate:
    """A single modality's opinion that something happened."""

    modality: str
    t_start_ms: float
    t_end_ms: float
    score: float

    @property
    def t_center_ms(self) -> float:
        return 0.5 * (self.t_start_ms + self.t_end_ms)


@dataclass
class DetectedEvent:
    t_start_ms: int
    t_end_ms: int
    confidence: float
    modality_votes: dict[str, float]


@dataclass
class Derived:
    """The 100 Hz representation the last three stages work on.

    Roughly 100 MB for an eight-hour night in float32, versus ~1.4 GB of raw
    waveform, which is why raw storage is opt-in and this is not.
    """

    fs: float = DERIVED_FS
    acoustic_env: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    snore_env: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    semg_env: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    imu_si: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    imu_dyn: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    resp_volume: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    gx: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    gy: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    gz: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    present: np.ndarray = field(default_factory=lambda: np.zeros(0, bool))
    semg_ok: np.ndarray = field(default_factory=lambda: np.zeros(0, bool))
    # Filled in by stage 2.
    gated: np.ndarray = field(default_factory=lambda: np.zeros(0, bool))
    snoring: np.ndarray = field(default_factory=lambda: np.zeros(0, bool))

    ARRAYS = (
        "acoustic_env",
        "snore_env",
        "semg_env",
        "imu_si",
        "imu_dyn",
        "resp_volume",
        "gx",
        "gy",
        "gz",
        "present",
        "semg_ok",
        "gated",
        "snoring",
    )

    def __len__(self) -> int:
        return len(self.acoustic_env)

    @property
    def duration_ms(self) -> int:
        return int(len(self) / self.fs * 1000)

    def t_ms(self) -> np.ndarray:
        return np.arange(len(self)) * (1000.0 / self.fs)

    def index(self, t_ms: float) -> int:
        return int(np.clip(round(t_ms / 1000.0 * self.fs), 0, max(0, len(self) - 1)))

    def to_dict(self) -> dict[str, np.ndarray]:
        return {name: getattr(self, name) for name in self.ARRAYS}

    @classmethod
    def from_dict(cls, data: dict[str, np.ndarray], fs: float = DERIVED_FS) -> "Derived":
        return cls(fs=fs, **{k: v for k, v in data.items() if k in cls.ARRAYS})

    def extend(self, other: "Derived") -> None:
        for name in self.ARRAYS:
            mine, theirs = getattr(self, name), getattr(other, name)
            if len(theirs):
                setattr(self, name, np.concatenate([mine, theirs]))

    def pad_to(self, n: int) -> None:
        """Fill a gap with zeros marked absent, so coverage stays honest."""
        missing = n - len(self)
        if missing <= 0:
            return
        for name in self.ARRAYS:
            arr = getattr(self, name)
            fill = np.zeros(missing, dtype=arr.dtype)
            setattr(self, name, np.concatenate([arr, fill]))


@runtime_checkable
class SwallowDetector(Protocol):
    version: str

    def process_chunk(self, seq: int, t_start_ms: int, channels: dict, fs: dict) -> Derived:
        """Stage 1 only: reduce one full-rate chunk to its derived series."""

    def finalize(self, derived: Derived) -> list[DetectedEvent]:
        """Stages 2-4 over the whole night."""
