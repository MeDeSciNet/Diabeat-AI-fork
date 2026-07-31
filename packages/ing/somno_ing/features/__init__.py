"""Feature computation (PRD 6.3).

Turns a detected event list plus the derived series into the four things the
risk engine consumes: swallow-free interval burden, swallow-respiration
coordination, supine burden, and arousal decoupling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from ..detect.base import Derived, DetectedEvent

AROUSAL_WINDOW_MS = 10_000
FEATURE_VERSION = "features-v1.0.0"


@dataclass
class EventAnnotation:
    sleep_stage: str = "UNKNOWN"
    arousal_linked: bool = False
    arousal_id: str | None = None
    resp_phase_before: str = "UNKNOWN"
    resp_phase_after: str = "UNKNOWN"
    coordination_pattern: str = "UNKNOWN"
    swallow_apnea_ms: int | None = None
    posture: str = "UNKNOWN"
    hob_angle_deg: float | None = None


@dataclass
class NightFeatures:
    n_events: int = 0
    analysable_ms: int = 0
    swallows_per_hour: float = 0.0
    sfi_p50_s: float = 0.0
    sfi_p90_s: float = 0.0
    sfi_p95_s: float = 0.0
    sfi_max_s: float = 0.0
    sfi_burden: float = 0.0
    coordination_counts: dict[str, int] = field(default_factory=dict)
    coordination_anomaly: float = 0.0
    supine_burden: float = 0.0
    posture_ratios: dict[str, float] = field(default_factory=dict)
    mean_hob_angle_deg: float | None = None
    arousal_coupling: float = 0.0
    arousal_decoupling: float = 0.0
    snore_ratio: float = 0.0
    version: str = FEATURE_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ posture
def posture_from_gravity(gx: float, gy: float, gz: float) -> tuple[str, float]:
    norm = float(np.sqrt(gx * gx + gy * gy + gz * gz)) or 1.0
    gx, gy, gz = gx / norm, gy / norm, gz / norm
    hob = float(np.degrees(np.arcsin(np.clip(-gz, -1.0, 1.0))))
    if hob >= 60.0:
        return "upright", hob
    if abs(gx) >= abs(gy):
        return ("supine" if gx < 0 else "prone"), max(0.0, hob)
    return ("left" if gy < 0 else "right"), max(0.0, hob)


def posture_series(d: Derived) -> tuple[np.ndarray, np.ndarray]:
    """Per-sample posture label and head-of-bed angle."""
    n = len(d)
    if n == 0:
        return np.empty(0, dtype=object), np.zeros(0)
    g = np.stack([d.gx, d.gy, d.gz]).astype(np.float64)
    norm = np.linalg.norm(g, axis=0)
    norm[norm == 0] = 1.0
    gx, gy, gz = g / norm
    hob = np.degrees(np.arcsin(np.clip(-gz, -1.0, 1.0)))
    labels = np.where(
        hob >= 60.0,
        "upright",
        np.where(
            np.abs(gx) >= np.abs(gy),
            np.where(gx < 0, "supine", "prone"),
            np.where(gy < 0, "left", "right"),
        ),
    )
    return labels, np.maximum(hob, 0.0)


def posture_segments(d: Derived, min_ms: int = 60_000) -> list[dict]:
    labels, hob = posture_series(d)
    if len(labels) == 0:
        return []
    ms_per = 1000.0 / d.fs
    segs: list[dict] = []
    start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            segs.append(
                {
                    "t_start_ms": int(start * ms_per),
                    "t_end_ms": int(i * ms_per),
                    "posture": str(labels[start]),
                    "hob_angle_deg": round(float(np.median(hob[start:i])), 1),
                }
            )
            start = i
    # Absorb sub-minute flickers into the neighbour they interrupted.
    merged: list[dict] = []
    for seg in segs:
        if merged and seg["t_end_ms"] - seg["t_start_ms"] < min_ms:
            merged[-1]["t_end_ms"] = seg["t_end_ms"]
            continue
        if merged and merged[-1]["posture"] == seg["posture"]:
            merged[-1]["t_end_ms"] = seg["t_end_ms"]
            continue
        merged.append(dict(seg))
    return merged


# ------------------------------------------------------- respiration phases
def _slope(d: Derived) -> tuple[np.ndarray, np.ndarray]:
    vol = d.resp_volume.astype(np.float64)
    slope = np.gradient(vol) * d.fs
    from scipy.ndimage import median_filter

    scale = median_filter(np.abs(slope), size=max(3, int(60 * d.fs) | 1), mode="nearest")
    return slope, scale


def annotate_events(
    events: list[DetectedEvent],
    d: Derived,
    epochs: list[dict] | None = None,
    arousals: list[dict] | None = None,
) -> list[EventAnnotation]:
    slope, scale = _slope(d)
    labels, hob = posture_series(d)
    out: list[EventAnnotation] = []

    for ev in events:
        ann = EventAnnotation()
        i0 = d.index(ev.t_start_ms)

        before = _phase_of(slope, scale, d, ev.t_start_ms - 800, ev.t_start_ms - 250)
        apnea_end_ms = _apnea_end(slope, scale, d, ev.t_start_ms)
        after = (
            _phase_of(slope, scale, d, apnea_end_ms + 50, apnea_end_ms + 400)
            if apnea_end_ms is not None
            else "UNKNOWN"
        )
        ann.resp_phase_before = before
        ann.resp_phase_after = after
        ann.coordination_pattern = (
            f"{before}-{after}" if "UNKNOWN" not in (before, after) else "UNKNOWN"
        )
        if apnea_end_ms is not None:
            ann.swallow_apnea_ms = int(max(0, apnea_end_ms - ev.t_start_ms))

        if len(labels):
            ann.posture = str(labels[i0])
            ann.hob_angle_deg = round(float(hob[i0]), 1)

        if epochs:
            ann.sleep_stage = _stage_at(epochs, ev.t_start_ms)
        if arousals:
            hit = _arousal_at(arousals, ev.t_start_ms)
            ann.arousal_linked = hit is not None
            ann.arousal_id = hit
        out.append(ann)
    return out


def _phase_of(slope, scale, d: Derived, t0_ms: float, t1_ms: float) -> str:
    a, b = d.index(t0_ms), d.index(t1_ms)
    if b <= a:
        return "UNKNOWN"
    seg = slope[a:b]
    ref = float(np.median(scale[a:b])) + 1e-12
    mean = float(np.mean(seg))
    if abs(mean) < 0.25 * ref:
        return "UNKNOWN"
    # Rising lung volume is inspiration.
    return "I" if mean > 0 else "E"


def _apnea_end(slope, scale, d: Derived, onset_ms: float, max_ms: float = 3500.0) -> float | None:
    """First sustained resumption of airflow after the swallow."""
    a = d.index(onset_ms + 150)
    b = d.index(onset_ms + max_ms)
    if b <= a:
        return None
    ref = float(np.median(scale[a:b])) + 1e-12
    active = np.abs(slope[a:b]) > 0.45 * ref
    need = max(2, int(0.10 * d.fs))
    run = 0
    for i, ok in enumerate(active):
        run = run + 1 if ok else 0
        if run >= need:
            return (a + i - need + 1) * (1000.0 / d.fs)
    return None


def _stage_at(epochs: list[dict], t_ms: float) -> str:
    idx = int(t_ms // 30_000)
    if 0 <= idx < len(epochs):
        return epochs[idx].get("stage", "UNKNOWN")
    return "UNKNOWN"


def _arousal_at(arousals: list[dict], t_ms: float) -> str | None:
    for a in arousals:
        if abs(t_ms - a["t_start_ms"]) <= AROUSAL_WINDOW_MS:
            return a.get("id")
    return None


# ----------------------------------------------------------------- night
def compute(
    events: list[DetectedEvent],
    annotations: list[EventAnnotation],
    d: Derived,
    arousals: list[dict] | None,
    sfi_reference_s: float = 600.0,
) -> NightFeatures:
    f = NightFeatures()
    duration_ms = d.duration_ms
    analysable = int((~d.gated).sum() / d.fs * 1000) if len(d) else 0
    f.n_events = len(events)
    f.analysable_ms = analysable
    hours = max(analysable / 3_600_000, 1e-9)
    f.swallows_per_hour = round(len(events) / hours, 3)

    # Swallow-free intervals, bounded by session start and end.
    onsets = [e.t_start_ms for e in events]
    edges = [0.0, *onsets, float(duration_ms)]
    gaps = np.diff(edges) / 1000.0 if len(edges) > 1 else np.zeros(0)
    if len(gaps):
        f.sfi_p50_s = round(float(np.percentile(gaps, 50)), 1)
        f.sfi_p90_s = round(float(np.percentile(gaps, 90)), 1)
        f.sfi_p95_s = round(float(np.percentile(gaps, 95)), 1)
        f.sfi_max_s = round(float(gaps.max()), 1)
        long_time = float(gaps[gaps > sfi_reference_s].sum())
        f.sfi_burden = round(long_time / max(duration_ms / 1000.0, 1e-9), 4)

    counts: dict[str, int] = {}
    for ann in annotations:
        counts[ann.coordination_pattern] = counts.get(ann.coordination_pattern, 0) + 1
    f.coordination_counts = counts
    classified = sum(v for k, v in counts.items() if k != "UNKNOWN")
    # A swallow followed by inspiration is the risk-associated pattern.
    anomalous = sum(v for k, v in counts.items() if k.endswith("-I"))
    f.coordination_anomaly = round(anomalous / classified, 4) if classified else 0.0

    labels, hob = posture_series(d)
    if len(labels):
        usable = ~d.gated
        total = max(int(usable.sum()), 1)
        for name in ("supine", "left", "right", "prone", "upright"):
            f.posture_ratios[name] = round(float(((labels == name) & usable).sum() / total), 4)
        f.supine_burden = round(
            float(((labels == "supine") & (hob < 30.0) & usable).sum() / total), 4
        )
        f.mean_hob_angle_deg = round(float(np.mean(hob[usable])), 1) if usable.any() else None
    if len(d):
        f.snore_ratio = round(float(d.snoring.mean()), 4)

    if arousals and events:
        linked = sum(1 for a in annotations if a.arousal_linked)
        f.arousal_coupling = round(linked / len(events), 4)
    return f
