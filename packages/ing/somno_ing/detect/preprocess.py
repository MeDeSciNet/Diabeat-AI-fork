"""Stage 1 - preprocessing.

Runs on full-rate data, chunk by chunk, with filter state carried across chunk
boundaries. Its only job is to hand stages 2-4 a compact 100 Hz representation:
band envelopes, laryngeal motion, gravity, and a respiration proxy.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from .base import DERIVED_FS, Derived

# Swallow sound sits well above the snore band; separating them here means
# snoring can be flagged without gating out the periods it occurs in.
SWALLOW_BAND = (300.0, 3000.0)
SNORE_BAND = (60.0, 300.0)
SEMG_BAND = (20.0, 450.0)
RESP_BAND = (0.10, 0.60)
GRAVITY_CUTOFF = 0.30
MAINS_HZ = 50.0


class Preprocessor:
    """Stateful across chunks. One instance per session."""

    def __init__(self, fs: dict[str, float]) -> None:
        self.fs = fs
        fa = fs["acoustic"]
        fe = fs["semg"]
        fi = fs["imu_ax"]

        self._sos = {
            "swallow": sps.butter(4, SWALLOW_BAND, btype="bandpass", fs=fa, output="sos"),
            "snore": sps.butter(4, SNORE_BAND, btype="bandpass", fs=fa, output="sos"),
            "semg": sps.butter(4, SEMG_BAND, btype="bandpass", fs=fe, output="sos"),
            "gravity": sps.butter(2, GRAVITY_CUTOFF, btype="lowpass", fs=fi, output="sos"),
            "imu_lp": sps.butter(4, min(20.0, fi / 2.5), btype="lowpass", fs=fi, output="sos"),
        }
        self._zi = {k: sps.sosfilt_zi(v) * 0.0 for k, v in self._sos.items()}
        # Gravity starts at rest on the assumption of supine-flat; a couple of
        # seconds of settling at session start is not worth special-casing.
        self._zi_grav = {ax: sps.sosfilt_zi(self._sos["gravity"]) * 0.0 for ax in "xyz"}
        b, a = sps.iirnotch(MAINS_HZ, Q=30.0, fs=fe)
        self._notch = sps.tf2sos(b, a)
        self._zi_notch = sps.sosfilt_zi(self._notch) * 0.0

    # ------------------------------------------------------------------ api
    def process(self, channels: dict[str, np.ndarray], electrode_ok: bool = True) -> Derived:
        n_out = self._out_len(channels)
        d = Derived(fs=DERIVED_FS)

        ac = np.asarray(channels["acoustic"], dtype=np.float64)
        sw, self._zi["swallow"] = sps.sosfilt(self._sos["swallow"], ac, zi=self._zi["swallow"])
        sn, self._zi["snore"] = sps.sosfilt(self._sos["snore"], ac, zi=self._zi["snore"])
        d.acoustic_env = _rms_decimate(sw, self.fs["acoustic"], n_out)
        d.snore_env = _rms_decimate(sn, self.fs["acoustic"], n_out)

        emg = np.asarray(channels["semg"], dtype=np.float64)
        emg, self._zi_notch = sps.sosfilt(self._notch, emg, zi=self._zi_notch)
        emg, self._zi["semg"] = sps.sosfilt(self._sos["semg"], emg, zi=self._zi["semg"])
        d.semg_env = _rms_decimate(emg, self.fs["semg"], n_out)

        ax = np.asarray(channels["imu_ax"], dtype=np.float64)
        ay = np.asarray(channels["imu_ay"], dtype=np.float64)
        az = np.asarray(channels["imu_az"], dtype=np.float64)

        gx, self._zi_grav["x"] = sps.sosfilt(self._sos["gravity"], ax, zi=self._zi_grav["x"])
        gy, self._zi_grav["y"] = sps.sosfilt(self._sos["gravity"], ay, zi=self._zi_grav["y"])
        gz, self._zi_grav["z"] = sps.sosfilt(self._sos["gravity"], az, zi=self._zi_grav["z"])

        # Laryngeal excursion is what is left on the superior-inferior axis once
        # gravity is removed.
        si, self._zi["imu_lp"] = sps.sosfilt(self._sos["imu_lp"], az - gz, zi=self._zi["imu_lp"])
        # Respiration is stored RAW here and band-passed once, zero-phase, when
        # the night is complete - see finalize_resp().
        resp = ax
        dyn = np.sqrt((ax - gx) ** 2 + (ay - gy) ** 2 + (az - gz) ** 2)

        d.imu_si = _resample_to(si, self.fs["imu_ax"], n_out)
        d.imu_dyn = _resample_to(dyn, self.fs["imu_ax"], n_out)
        d.resp_volume = _resample_to(resp, self.fs["imu_ax"], n_out)
        d.gx = _resample_to(gx, self.fs["imu_ax"], n_out)
        d.gy = _resample_to(gy, self.fs["imu_ax"], n_out)
        d.gz = _resample_to(gz, self.fs["imu_ax"], n_out)

        d.present = np.ones(n_out, dtype=bool)
        d.semg_ok = np.full(n_out, bool(electrode_ok))
        d.gated = np.zeros(n_out, dtype=bool)
        d.snoring = np.zeros(n_out, dtype=bool)
        return d

    def _out_len(self, channels: dict[str, np.ndarray]) -> int:
        n_ms = len(channels["imu_ax"]) / self.fs["imu_ax"] * 1000.0
        return int(round(n_ms / 1000.0 * DERIVED_FS))


def _rms_decimate(x: np.ndarray, fs: float, n_out: int) -> np.ndarray:
    """Block RMS - the envelope measure that matters for a burst-like event."""
    if n_out <= 0:
        return np.zeros(0, np.float32)
    block = max(1, int(round(len(x) / n_out)))
    usable = block * n_out
    if usable > len(x):
        x = np.pad(x, (0, usable - len(x)))
    seg = x[:usable].reshape(n_out, block)
    return np.sqrt(np.mean(seg * seg, axis=1)).astype(np.float32)


def _resample_to(x: np.ndarray, fs: float, n_out: int) -> np.ndarray:
    if n_out <= 0:
        return np.zeros(0, np.float32)
    if len(x) == n_out:
        return x.astype(np.float32)
    idx = np.linspace(0, len(x) - 1, n_out)
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


def finalize_resp(d) -> None:
    """Band-pass the respiration channel across the whole night, zero-phase.

    This cannot be part of stage 1. A causal 0.1-0.6 Hz Butterworth has ~0.95 s
    of group delay at a normal breathing rate - close to a quarter of a breath -
    which shifts every phase measurement enough to make the coordination pattern
    little better than a guess. Filtering forwards and backwards once the session
    is closed costs one pass over a 100 Hz array and has no delay at all.

    Called exactly once, from SessionIngestor.finish(), before the derived series
    is persisted. Re-analysis reads the already-filtered array, which is what
    keeps analysis idempotent.
    """
    x = np.asarray(d.resp_volume, dtype=np.float64)
    if len(x) < 100:
        return
    sos = sps.butter(2, RESP_BAND, btype="bandpass", fs=d.fs, output="sos")
    padlen = min(len(x) - 1, 3 * (sos.shape[0] * 2 + 1))
    d.resp_volume = sps.sosfiltfilt(sos, x, padlen=padlen).astype(np.float32)


def wavelet_denoise(x: np.ndarray, wavelet: str = "db4", level: int = 4) -> np.ndarray:
    """Soft-threshold denoise, applied to the envelope rather than the raw audio.

    The PRD asks for wavelet denoising of the acoustic channel. Doing it on the
    100 Hz envelope instead of 16 kHz raw costs 160x less compute, removes the
    chunk-boundary problem entirely, and targets the thing the detector actually
    thresholds. Denoising the raw waveform would be the right call only if a
    later stage looked at spectral shape within the burst.
    """
    import pywt

    if len(x) < 2**level:
        return x
    coeffs = pywt.wavedec(x, wavelet, level=level)
    # Universal threshold from the finest detail band's noise estimate.
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745 if len(coeffs[-1]) else 0.0
    thr = sigma * np.sqrt(2 * np.log(max(len(x), 2)))
    coeffs[1:] = [pywt.threshold(c, thr, mode="soft") for c in coeffs[1:]]
    out = pywt.waverec(coeffs, wavelet)
    return np.asarray(out[: len(x)], dtype=np.float32)
