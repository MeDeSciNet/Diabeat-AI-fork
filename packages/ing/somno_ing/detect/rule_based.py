"""The v1 detector: rule-based, configuration-driven, no learned parameters.

Implements ``SwallowDetector``. Every threshold comes from a YAML file rather
than the source, so retuning does not require a release, and a v2 ``MLDetector``
can be dropped in behind the same interface without touching ingest or the
analysis pipeline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from ..settings import get_settings
from . import candidates as cand
from . import gating
from .base import Candidate, Derived, DetectedEvent
from .fusion import FusionConfig, fuse
from .preprocess import Preprocessor

DETECTOR_VERSION = "detect-rule-v1.0.0"


class RuleBasedDetector:
    version = DETECTOR_VERSION

    def __init__(self, config_path: Path | None = None, fs: dict[str, float] | None = None) -> None:
        raw = {}
        path = Path(config_path or get_settings().detector_config)
        if path.exists():
            raw = yaml.safe_load(path.read_text()) or {}
        self.gating_cfg = gating.GatingConfig(**raw.get("gating", {}))
        self.candidate_cfg = cand.CandidateConfig(**raw.get("candidates", {}))
        self.fusion_cfg = FusionConfig(**raw.get("fusion", {}))
        self._pre = Preprocessor(fs) if fs else None
        self.last_gating: gating.GatingResult | None = None
        self.last_candidates: list[Candidate] = []

    # ------------------------------------------------------------- stage 1
    def process_chunk(
        self, seq: int, t_start_ms: int, channels: dict, fs: dict, electrode_ok: bool = True
    ) -> Derived:
        if self._pre is None:
            self._pre = Preprocessor(fs)
        return self._pre.process(channels, electrode_ok=electrode_ok)

    # ---------------------------------------------------------- stages 2-4
    def finalize(self, derived: Derived) -> list[DetectedEvent]:
        self.last_gating = gating.apply(derived, self.gating_cfg)
        cands = (
            cand.acoustic_candidates(derived, self.candidate_cfg)
            + cand.imu_candidates(derived, self.candidate_cfg)
            + cand.semg_candidates(derived, self.candidate_cfg)
        )
        self.last_candidates = cands
        return fuse(cands, derived, self.fusion_cfg)


def build_detector(fs: dict[str, float] | None = None) -> RuleBasedDetector:
    """Factory. A v2 would select the implementation here from configuration."""
    return RuleBasedDetector(fs=fs)


def detect_from_derived(derived: Derived) -> tuple[list[DetectedEvent], gating.GatingResult]:
    """Convenience for offline re-analysis of a stored derived series."""
    det = RuleBasedDetector()
    events = det.finalize(derived)
    assert det.last_gating is not None
    return events, det.last_gating


__all__ = [
    "DETECTOR_VERSION",
    "RuleBasedDetector",
    "build_detector",
    "detect_from_derived",
    "np",
]
