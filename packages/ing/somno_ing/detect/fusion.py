"""Stage 4 - fusion and adjudication.

Candidates from the three modalities are clustered in time and voted on. The
weights are configurable, but the structural rule is not: a single modality
never carries an event on its own while a second one is available. That is what
keeps snoring (acoustic only) and a restless sleeper (IMU only) out of the
event list.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .base import Candidate, Derived, DetectedEvent


@dataclass
class FusionConfig:
    weights: dict[str, float] = field(
        default_factory=lambda: {"acoustic": 0.4, "imu": 0.3, "semg": 0.3}
    )
    tolerance_ms: float = 300.0
    confidence_threshold: float = 0.50
    min_modalities: int = 2


def fuse(candidates: list[Candidate], d: Derived, cfg: FusionConfig) -> list[DetectedEvent]:
    if not candidates:
        return []
    ordered = sorted(candidates, key=lambda c: c.t_center_ms)

    clusters: list[list[Candidate]] = []
    for cand in ordered:
        if clusters and cand.t_center_ms - clusters[-1][-1].t_center_ms <= cfg.tolerance_ms:
            clusters[-1].append(cand)
        else:
            clusters.append([cand])

    events: list[DetectedEvent] = []
    for cluster in clusters:
        # Keep the strongest candidate per modality within the cluster.
        best: dict[str, Candidate] = {}
        for c in cluster:
            if c.modality not in best or c.score > best[c.modality].score:
                best[c.modality] = c

        centre = float(np.mean([c.t_center_ms for c in best.values()]))
        available = _available_modalities(d, centre, cfg)
        weight_sum = sum(cfg.weights[m] for m in available) or 1.0
        votes = {m: round(float(c.score), 4) for m, c in best.items() if m in available}
        if not votes:
            continue

        confidence = sum(cfg.weights[m] * s for m, s in votes.items()) / weight_sum
        need = min(cfg.min_modalities, len(available))
        if len(votes) < need or confidence < cfg.confidence_threshold:
            continue

        contributing = [best[m] for m in votes]
        events.append(
            DetectedEvent(
                t_start_ms=int(min(c.t_start_ms for c in contributing)),
                t_end_ms=int(max(c.t_end_ms for c in contributing)),
                confidence=round(float(min(1.0, confidence)), 4),
                modality_votes=votes,
            )
        )
    return events


def _available_modalities(d: Derived, t_ms: float, cfg: FusionConfig) -> list[str]:
    """Which modalities were actually usable at this instant.

    Re-normalising over available modalities means a night that loses the sEMG
    electrode is judged on the two channels it still has, instead of quietly
    failing every confidence check for the rest of the recording.
    """
    i = d.index(t_ms)
    out = ["acoustic", "imu"]
    if len(d.semg_ok) and bool(d.semg_ok[i]):
        out.append("semg")
    return out
