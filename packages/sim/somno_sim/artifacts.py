"""Interference and noise injection (SIM-3).

Each artifact is independently switchable so the detector can be stress-tested
one confounder at a time. Speech and snoring matter most: both put energy in the
swallow band, and speech also drives the submental muscles that carry the sEMG
signature, so it is the hardest true confounder in the set.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sps

from .config import Scenario
from .physiology import Night
from .rng import chunk_stream, stream


@dataclass
class Span:
    t_start_ms: int
    t_end_ms: int


class ArtifactEngine:
    def __init__(self, cfg: Scenario, night: Night, seed: int) -> None:
        self.cfg = cfg
        self.night = night
        self.seed = seed
        rng = stream(seed, "artifact")
        a = cfg.artifacts

        self.speech_spans: list[Span] = []
        if a.speech.enabled:
            # Pre-sleep conversation, plus the occasional sleep-talking burst.
            n_bursts = 1 + int(a.speech.intensity * 4)
            starts = np.sort(rng.uniform(0, min(cfg.duration_ms, 40 * 60_000), size=n_bursts))
            for s in starts:
                dur = rng.uniform(20_000, 90_000)
                self.speech_spans.append(Span(int(s), int(min(s + dur, cfg.duration_ms))))

        self.movement_spans: list[Span] = []
        if a.body_movement.enabled:
            for seg in night.postures[1:]:
                self.movement_spans.append(
                    Span(seg.t_start_ms - 1500, seg.t_start_ms + cfg.posture.transition_ms + 1500)
                )
            extra = int(a.body_movement.intensity * cfg.duration_ms / 600_000)
            for s in rng.uniform(0, cfg.duration_ms, size=max(0, extra)):
                self.movement_spans.append(Span(int(s), int(s + rng.uniform(1500, 5000))))

        self.snore_spans: list[Span] = []
        if a.snoring.enabled:
            # Snoring tracks supine NREM, which is also when supine burden is worst.
            for seg in night.postures:
                if seg.posture != "supine":
                    continue
                if rng.random() < 0.4 + 0.5 * a.snoring.intensity:
                    self.snore_spans.append(Span(seg.t_start_ms, seg.t_end_ms))

        self.detach_at_ms = (
            int(a.electrode_detach.at_min * 60_000) if a.electrode_detach.enabled else None
        )
        self.hr_hz = float(rng.uniform(0.9, 1.15))
        self._sos_snore = sps.butter(
            4, [60, 300], btype="bandpass", fs=cfg.signal.acoustic_fs_hz, output="sos"
        )
        self._sos_speech = sps.butter(
            4, [150, 3000], btype="bandpass", fs=cfg.signal.acoustic_fs_hz, output="sos"
        )
        self._sos_semg = sps.butter(
            4, [20, 450], btype="bandpass", fs=cfg.signal.semg_fs_hz, output="sos"
        )

    # ------------------------------------------------------------------ api
    def electrode_ok(self, t_ms: float) -> bool:
        return self.detach_at_ms is None or t_ms < self.detach_at_ms

    def apply(self, out: dict[str, np.ndarray], seq: int, t0_ms: int, t1_ms: int) -> None:
        cfg = self.cfg
        s = cfg.signal
        a = cfg.artifacts
        rng = chunk_stream(self.seed, "artifact", seq)

        t_ac = _grid(t0_ms, t1_ms, s.acoustic_fs_hz)
        t_imu = _grid(t0_ms, t1_ms, s.imu_fs_hz)
        t_emg = _grid(t0_ms, t1_ms, s.semg_fs_hz)

        if a.cardiac.enabled:
            self._cardiac(out, t_ac, t_emg, a.cardiac.intensity)
        if self.snore_spans:
            self._snoring(out, rng, t_ac, a.snoring.intensity)
        if self.speech_spans:
            self._speech(out, rng, t_ac, t_emg, a.speech.intensity)
        if self.movement_spans:
            self._movement(out, rng, t_ac, t_imu, t_emg, a.body_movement.intensity)
        if a.sweat_drift.enabled:
            out["semg"] += 40.0 * a.sweat_drift.intensity * np.sin(
                2 * np.pi * t_emg / 1000.0 / 420.0 + 0.7
            )
        if self.detach_at_ms is not None:
            self._detach(out, rng, t_emg)

    # ------------------------------------------------------------ artifacts
    def _cardiac(self, out, t_ac, t_emg, intensity: float) -> None:
        beat = np.mod(t_ac / 1000.0 * self.hr_hz, 1.0)
        thump = np.exp(-((beat / 0.045) ** 2)) * np.sin(2 * np.pi * 45 * t_ac / 1000.0)
        out["acoustic"] += 0.010 * intensity * thump
        beat_e = np.mod(t_emg / 1000.0 * self.hr_hz, 1.0)
        out["semg"] += 12.0 * intensity * np.exp(-((beat_e / 0.02) ** 2))

    def _snoring(self, out, rng, t_ac, intensity: float) -> None:
        mask = _span_mask(t_ac, self.snore_spans)
        if not mask.any():
            return
        # Snores ride on inspiration, so they are locked to the breathing cycle.
        phi = self.night.resp_phase(t_ac)
        env = np.clip(np.sin(np.pi * np.clip(phi / 0.5, 0, 1)), 0, 1) ** 2
        noise = sps.sosfiltfilt(self._sos_snore, rng.standard_normal(len(t_ac)))
        noise /= np.std(noise) + 1e-12
        out["acoustic"] += mask * env * noise * 0.11 * intensity

    def _speech(self, out, rng, t_ac, t_emg, intensity: float) -> None:
        mask = _span_mask(t_ac, self.speech_spans)
        if mask.any():
            syllable = 0.5 * (1 + np.sin(2 * np.pi * 4.2 * t_ac / 1000.0))
            noise = sps.sosfiltfilt(self._sos_speech, rng.standard_normal(len(t_ac)))
            noise /= np.std(noise) + 1e-12
            out["acoustic"] += mask * syllable * noise * 0.07 * (0.4 + intensity)
        mask_e = _span_mask(t_emg, self.speech_spans)
        if mask_e.any():
            # Speech recruits the same submental muscles a swallow does.
            syl_e = 0.5 * (1 + np.sin(2 * np.pi * 4.2 * t_emg / 1000.0))
            burst = sps.sosfiltfilt(self._sos_semg, rng.standard_normal(len(t_emg)))
            burst *= 1.0 / (np.std(burst) + 1e-12)
            out["semg"] += mask_e * syl_e * burst * 35.0 * (0.4 + intensity)

    def _movement(self, out, rng, t_ac, t_imu, t_emg, intensity: float) -> None:
        for arr, t in (("acoustic", t_ac), ("semg", t_emg)):
            mask = _span_mask(t, self.movement_spans)
            if mask.any():
                amp = 0.05 * intensity if arr == "acoustic" else 45.0 * intensity
                out[arr] += mask * rng.normal(0, amp, len(t))
        mask_i = _span_mask(t_imu, self.movement_spans)
        if mask_i.any():
            for ax in ("imu_ax", "imu_ay", "imu_az"):
                out[ax] += mask_i * rng.normal(0, 0.25 * intensity, len(t_imu))
            for ax in ("imu_gx", "imu_gy", "imu_gz"):
                out[ax] += mask_i * rng.normal(0, 60.0 * intensity, len(t_imu))

    def _detach(self, out, rng, t_emg) -> None:
        after = t_emg >= self.detach_at_ms
        if not after.any():
            return
        # A detached electrode does not go quiet: it rails and drifts.
        out["semg"][after] = 0.0
        ramp = np.clip((t_emg[after] - self.detach_at_ms) / 5000.0, 0, 1)
        out["semg"][after] += ramp * 180.0 * np.sin(2 * np.pi * t_emg[after] / 1000.0 / 90.0)
        out["semg"][after] += rng.normal(0, 2.0, int(after.sum()))


def _grid(t0_ms: int, t1_ms: int, fs: int) -> np.ndarray:
    n = int(round((t1_ms - t0_ms) / 1000.0 * fs))
    return t0_ms + np.arange(n) * (1000.0 / fs)


def _span_mask(t_ms: np.ndarray, spans: list[Span]) -> np.ndarray:
    mask = np.zeros(len(t_ms), dtype=float)
    if len(t_ms) == 0:
        return mask
    lo, hi = t_ms[0], t_ms[-1]
    for sp in spans:
        if sp.t_end_ms < lo or sp.t_start_ms > hi:
            continue
        mask[(t_ms >= sp.t_start_ms) & (t_ms < sp.t_end_ms)] = 1.0
    return mask
