"""Stage 3 - per-modality candidate detection.

Each modality decides independently and knows nothing about the others; that is
what makes the stage-4 vote worth anything. All three use a rolling
median/MAD baseline rather than a fixed threshold, because the noise floor
drifts across a night (posture changes, sweat, electrode settling).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .base import Candidate, Derived
from .preprocess import wavelet_denoise


@dataclass
class CandidateConfig:
    baseline_window_s: float = 30.0
    acoustic_k: float = 5.0
    acoustic_k_snoring: float = 7.5
    acoustic_min_ms: float = 80.0
    imu_ncc: float = 0.50
    imu_template_ms: float = 900.0
    semg_k: float = 4.0
    semg_min_ms: float = 150.0
    merge_gap_ms: float = 150.0
    max_event_ms: float = 2500.0


def acoustic_candidates(d: Derived, cfg: CandidateConfig) -> list[Candidate]:
    env = wavelet_denoise(d.acoustic_env.astype(np.float32))
    z = _robust_z(env.astype(np.float64), int(cfg.baseline_window_s * d.fs))
    thr = np.where(d.snoring, cfg.acoustic_k_snoring, cfg.acoustic_k)
    hits = (z > thr) & ~d.gated
    return _spans_to_candidates(
        "acoustic", hits, z, d, cfg, min_ms=cfg.acoustic_min_ms, full_scale=2.5 * cfg.acoustic_k
    )


def imu_candidates(d: Derived, cfg: CandidateConfig) -> list[Candidate]:
    """Template match against the biphasic hyoid-laryngeal excursion."""
    tpl = biphasic_template(cfg.imu_template_ms, d.fs)
    ncc = _normalised_xcorr(d.imu_si.astype(np.float64), tpl)
    hits = (ncc > cfg.imu_ncc) & ~d.gated
    return _spans_to_candidates(
        "imu", hits, ncc, d, cfg, min_ms=200.0, full_scale=1.0, align_peak=True
    )


def semg_candidates(d: Derived, cfg: CandidateConfig) -> list[Candidate]:
    z = _robust_z(d.semg_env.astype(np.float64), int(cfg.baseline_window_s * d.fs))
    hits = (z > cfg.semg_k) & ~d.gated & d.semg_ok
    return _spans_to_candidates(
        "semg", hits, z, d, cfg, min_ms=cfg.semg_min_ms, full_scale=2.5 * cfg.semg_k
    )


def biphasic_template(duration_ms: float, fs: float) -> np.ndarray:
    """Rise then slightly slower fall - the shape the larynx traces on the S-I axis."""
    n = max(4, int(duration_ms / 1000.0 * fs))
    t = np.arange(n) / fs
    dur = duration_ms / 1000.0
    up = np.exp(-(((t - 0.20 * dur) / (0.10 * dur)) ** 2))
    down = np.exp(-(((t - 0.61 * dur) / (0.12 * dur)) ** 2))
    k = up - 0.85 * down
    k -= k.mean()
    return k / (np.linalg.norm(k) + 1e-12)


# ---------------------------------------------------------------- internals
def _robust_z(x: np.ndarray, window: int) -> np.ndarray:
    """Median/MAD z-score against a rolling baseline."""
    from scipy.ndimage import median_filter

    window = max(3, window | 1)
    med = median_filter(x, size=window, mode="nearest")
    mad = median_filter(np.abs(x - med), size=window, mode="nearest")
    return (x - med) / (1.4826 * mad + 1e-9)


def _normalised_xcorr(x: np.ndarray, tpl: np.ndarray) -> np.ndarray:
    n = len(tpl)
    if len(x) < n:
        return np.zeros(len(x))
    corr = np.correlate(x, tpl, mode="same")
    # Local energy for normalisation, over the same support as the template.
    energy = np.sqrt(np.convolve(x * x, np.ones(n), mode="same"))
    ncc = corr / (energy + 1e-12)
    return np.clip(ncc, -1.0, 1.0)


def _spans_to_candidates(
    modality: str,
    hits: np.ndarray,
    score: np.ndarray,
    d: Derived,
    cfg: CandidateConfig,
    min_ms: float,
    full_scale: float,
    align_peak: bool = False,
) -> list[Candidate]:
    out: list[Candidate] = []
    ms_per = 1000.0 / d.fs
    merge = int(cfg.merge_gap_ms / ms_per)
    for a, b in _spans(hits, merge):
        dur_ms = (b - a) * ms_per
        if dur_ms < min_ms:
            continue
        if dur_ms > cfg.max_event_ms:
            b = a + int(cfg.max_event_ms / ms_per)
        peak = a + int(np.argmax(score[a:b])) if b > a else a
        t0, t1 = a * ms_per, b * ms_per
        if align_peak:
            # A matched filter peaks at the template centre, so recover the onset.
            t0 = peak * ms_per - cfg.imu_template_ms / 2
            t1 = t0 + cfg.imu_template_ms
        out.append(
            Candidate(
                modality=modality,
                t_start_ms=float(max(0.0, t0)),
                t_end_ms=float(t1),
                score=float(np.clip(score[peak] / full_scale, 0.0, 1.0)),
            )
        )
    return out


def _spans(mask: np.ndarray, merge: int) -> list[tuple[int, int]]:
    if not mask.any():
        return []
    idx = np.flatnonzero(np.diff(np.concatenate([[0], mask.view(np.int8), [0]])))
    spans = list(zip(idx[::2], idx[1::2]))
    merged: list[list[int]] = []
    for a, b in spans:
        if merged and a - merged[-1][1] <= merge:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]
