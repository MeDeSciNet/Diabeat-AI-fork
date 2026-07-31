"""Stage 2 - interference gating.

Two classes of interference, treated differently on purpose:

* **Hard gate** (movement, speech, dead channel). The signal is unusable, the
  window is excluded from detection, and the time counts towards
  ``artifact_ratio``.
* **Soft flag** (snoring). The signal is still usable - snore energy lives at
  60-300 Hz and the swallow burst at 300-3000 Hz - so these windows keep
  participating in detection at a raised threshold. Hard-gating them would be
  the obvious reading of the PRD, but a supine snorer can snore through 70% of
  the night, which would gate away most of the recording and then trip the
  ``artifact_ratio > 0.4`` quality rule. A snorer is not an unanalysable
  recording, and treating them as one would silence the exact population the
  system exists for.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sps

from .base import Derived


@dataclass
class GatingConfig:
    movement_g: float = 0.08
    movement_window_s: float = 1.5
    movement_pad_s: float = 1.5
    speech_ratio: float = 0.42
    speech_window_s: float = 3.0
    speech_pad_s: float = 1.0
    snore_ratio: float = 1.1
    snore_window_s: float = 20.0


@dataclass
class GatingResult:
    artifact_ratio: float
    movement_ratio: float
    speech_ratio: float
    snore_ratio: float


def apply(d: Derived, cfg: GatingConfig | None = None) -> GatingResult:
    cfg = cfg or GatingConfig()
    n = len(d)
    if n == 0:
        return GatingResult(0.0, 0.0, 0.0, 0.0)
    fs = d.fs

    movement = _movement_mask(d, cfg, fs)
    speech = _speech_mask(d, cfg, fs)
    snoring = _snore_mask(d, cfg, fs)

    dead = ~d.present
    d.gated = movement | speech | dead
    d.snoring = snoring & ~d.gated

    return GatingResult(
        artifact_ratio=float(d.gated.mean()),
        movement_ratio=float(movement.mean()),
        speech_ratio=float(speech.mean()),
        snore_ratio=float(d.snoring.mean()),
    )


def _movement_mask(d: Derived, cfg: GatingConfig, fs: float) -> np.ndarray:
    """Sustained whole-body motion, not the swallow's own laryngeal excursion.

    A peak-based statistic cannot separate the two: hyoid elevation puts ~0.05 g
    on the S-I axis, which is the same order as a gentle repositioning. What
    differs is duration - a swallow is under a second, a body movement runs for
    several - so the window mean is the discriminator, and gating on the peak
    silently deletes true events.
    """
    w = max(1, int(cfg.movement_window_s * fs))
    energy = _rolling_mean(np.abs(d.imu_dyn.astype(np.float64)), w)
    mask = energy > cfg.movement_g
    return _dilate(mask, int(cfg.movement_pad_s * fs))


def _speech_mask(d: Derived, cfg: GatingConfig, fs: float) -> np.ndarray:
    """Speech is syllabic: its envelope carries sustained 3-6 Hz modulation.

    A swallow puts a single transient into the same band, so the discriminator
    is sustained modulation *energy relative to the local envelope level*, over
    a window several syllables long.
    """
    env = d.acoustic_env.astype(np.float64)
    if len(env) < int(4 * fs):
        return np.zeros(len(env), bool)
    sos = sps.butter(2, [2.5, min(7.0, fs / 2.5)], btype="bandpass", fs=fs, output="sos")
    mod = np.abs(sps.sosfiltfilt(sos, env))
    w = max(1, int(cfg.speech_window_s * fs))
    ratio = _rolling_mean(mod, w) / (_rolling_mean(env, w) + 1e-12)
    return _dilate(ratio > cfg.speech_ratio, int(cfg.speech_pad_s * fs))


def _snore_mask(d: Derived, cfg: GatingConfig, fs: float) -> np.ndarray:
    """Snore-band energy dominating the swallow band, sustained over 20 s.

    The floor is a low percentile of the night rather than its median: in a
    heavy snorer the median *is* the snoring level, so a median-based floor
    detects nothing in exactly the recordings the flag exists for.
    """
    w = max(1, int(cfg.snore_window_s * fs))
    snore = _rolling_mean(d.snore_env.astype(np.float64), w)
    swallow = _rolling_mean(d.acoustic_env.astype(np.float64), w)
    quiet = float(np.percentile(snore, 10))
    return (snore > cfg.snore_ratio * swallow) & (snore > max(3.0 * quiet, 1e-9))


# --------------------------------------------------------------- primitives
def _rolling_mean(x: np.ndarray, w: int) -> np.ndarray:
    if w <= 1:
        return x
    kernel = np.ones(w) / w
    return np.convolve(x, kernel, mode="same")


def _dilate(mask: np.ndarray, pad: int) -> np.ndarray:
    if pad <= 0 or not mask.any():
        return mask
    from scipy.ndimage import binary_dilation

    return binary_dilation(mask, structure=np.ones(2 * pad + 1, dtype=bool))
