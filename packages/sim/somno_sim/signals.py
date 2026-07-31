"""Signal layer: turns the physiology skeleton into waveforms.

Rendering is strictly chunk-by-chunk and in order, so an 8-hour night never
exists in memory at once. Filters carry their state across chunk boundaries,
which keeps the noise floor continuous - a step at every chunk edge would show
up as a detectable transient and quietly inflate the false-positive rate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sps

from . import artifacts as art
from .config import Scenario
from .physiology import Night
from .rng import chunk_stream, effective_seed

# Unit gravity vector per posture, in body axes:
#   x anterior(+)/posterior(-), y right(+)/left(-), z superior(+)/inferior(-)
_GRAVITY_FLAT = {
    "supine": (-1.0, 0.0),
    "prone": (1.0, 0.0),
    "left": (0.0, -1.0),
    "right": (0.0, 1.0),
}

CHANNELS = ("acoustic", "imu_ax", "imu_ay", "imu_az", "imu_gx", "imu_gy", "imu_gz", "semg")
CHANNEL_UNITS = {
    "acoustic": "a.u.",
    "semg": "uV",
    **{f"imu_{a}": "g" for a in ("ax", "ay", "az")},
    **{f"imu_{a}": "dps" for a in ("gx", "gy", "gz")},
}
# int16 quantisation step per channel: physical = int16 * scale.
CHANNEL_SCALE = {
    "acoustic": 1.0 / 32000.0,
    "semg": 400.0 / 32000.0,
    **{f"imu_{a}": 4.0 / 32000.0 for a in ("ax", "ay", "az")},
    **{f"imu_{a}": 500.0 / 32000.0 for a in ("gx", "gy", "gz")},
}


def gravity_vector(posture: str, hob_deg: float) -> tuple[float, float, float]:
    """Head-of-bed elevation tilts the body head-up, adding an inferior component."""
    if posture == "upright":
        return (0.0, 0.0, -1.0)
    gx, gy = _GRAVITY_FLAT.get(posture, _GRAVITY_FLAT["supine"])
    theta = np.deg2rad(hob_deg)
    return (gx * np.cos(theta), gy * np.cos(theta), -np.sin(theta))


@dataclass
class _Kernel:
    t_start_ms: int
    acoustic: np.ndarray
    imu_az: np.ndarray
    imu_gy: np.ndarray
    semg: np.ndarray


class Synthesizer:
    """Stateful, in-order chunk renderer."""

    def __init__(self, cfg: Scenario, night: Night, seed: int) -> None:
        self.cfg = cfg
        self.night = night
        self.seed = effective_seed(seed, cfg.scenario)
        s = cfg.signal

        self._sos_acoustic = sps.butter(4, [80, 4000], btype="bandpass", fs=s.acoustic_fs_hz, output="sos")
        self._zi_acoustic = sps.sosfilt_zi(self._sos_acoustic) * 0.0
        self._sos_breath = sps.butter(4, [200, 900], btype="bandpass", fs=s.acoustic_fs_hz, output="sos")
        self._zi_breath = sps.sosfilt_zi(self._sos_breath) * 0.0
        self._sos_semg = sps.butter(4, [20, 450], btype="bandpass", fs=s.semg_fs_hz, output="sos")
        self._zi_semg = sps.sosfilt_zi(self._sos_semg) * 0.0

        self._kernels = _build_kernels(cfg, night, seed)
        self._kernel_idx = 0
        self.artifacts = art.ArtifactEngine(cfg, night, seed)

    # ------------------------------------------------------------------ main
    def render(self, seq: int, t0_ms: int, t1_ms: int) -> dict[str, np.ndarray]:
        s = self.cfg.signal
        out: dict[str, np.ndarray] = {}

        t_ac = _time_grid(t0_ms, t1_ms, s.acoustic_fs_hz)
        t_imu = _time_grid(t0_ms, t1_ms, s.imu_fs_hz)
        t_emg = _time_grid(t0_ms, t1_ms, s.semg_fs_hz)

        out["acoustic"] = self._acoustic(seq, t_ac)
        out.update(self._imu(seq, t_imu))
        out["semg"] = self._semg(seq, t_emg)

        self._add_kernels(out, t0_ms, t1_ms)
        self.artifacts.apply(out, seq, t0_ms, t1_ms)
        return out

    # ------------------------------------------------------------- channels
    def _acoustic(self, seq: int, t_ms: np.ndarray) -> np.ndarray:
        s = self.cfg.signal
        rng = chunk_stream(self.seed, "acoustic", seq)
        n = len(t_ms)
        base, self._zi_acoustic = sps.sosfilt(
            self._sos_acoustic, rng.standard_normal(n), zi=self._zi_acoustic
        )
        base *= s.acoustic_noise / (np.std(base) + 1e-12)

        # Breath sound rides on airflow, i.e. the magnitude of dV/dt, and stops
        # during the swallow apnea.
        flow = self._airflow(t_ms)
        breath, self._zi_breath = sps.sosfilt(
            self._sos_breath, rng.standard_normal(n), zi=self._zi_breath
        )
        breath *= s.breath_acoustic_amp / (np.std(breath) + 1e-12)
        return base + breath * np.abs(flow)

    def _imu(self, seq: int, t_ms: np.ndarray) -> dict[str, np.ndarray]:
        s = self.cfg.signal
        rng = chunk_stream(self.seed, "imu", seq)
        n = len(t_ms)
        gx, gy, gz = self._gravity_series(t_ms)

        vol = self._volume(t_ms)
        resp = s.resp_imu_amp_g * (vol - 0.5)

        out = {
            "imu_ax": gx + resp + rng.normal(0, s.imu_noise_g, n),
            "imu_ay": gy + rng.normal(0, s.imu_noise_g, n),
            "imu_az": gz + rng.normal(0, s.imu_noise_g, n),
            "imu_gx": rng.normal(0, 0.4, n),
            "imu_gy": rng.normal(0, 0.4, n),
            "imu_gz": rng.normal(0, 0.4, n),
        }
        return out

    def _semg(self, seq: int, t_ms: np.ndarray) -> np.ndarray:
        s = self.cfg.signal
        rng = chunk_stream(self.seed, "semg", seq)
        n = len(t_ms)
        base, self._zi_semg = sps.sosfilt(
            self._sos_semg, rng.standard_normal(n), zi=self._zi_semg
        )
        base *= s.semg_noise_uv / (np.std(base) + 1e-12)
        mains = 3.0 * np.sin(2 * np.pi * 50.0 * t_ms / 1000.0)
        return base + mains

    # ------------------------------------------------------------- helpers
    def _volume(self, t_ms: np.ndarray) -> np.ndarray:
        """Lung volume in [0,1], held flat through each swallow apnea."""
        phi = self.night.resp_phase(t_ms)
        vol = 0.5 * (1.0 - np.cos(2 * np.pi * phi))
        for sw in self.night.swallows:
            a, b = sw.t_start_ms, sw.t_start_ms + sw.swallow_apnea_ms
            if b < t_ms[0] or a > t_ms[-1]:
                continue
            mask = (t_ms >= a) & (t_ms < b)
            if mask.any():
                held = 0.5 * (
                    1.0 - np.cos(2 * np.pi * self.night.resp_phase(np.array([float(a)]))[0])
                )
                vol[mask] = held
        return vol

    def _airflow(self, t_ms: np.ndarray) -> np.ndarray:
        vol = self._volume(t_ms)
        flow = np.gradient(vol) * len(t_ms) / max(1.0, (t_ms[-1] - t_ms[0]) / 1000.0)
        return flow / (np.percentile(np.abs(flow), 95) + 1e-9)

    def _gravity_series(self, t_ms: np.ndarray) -> tuple[np.ndarray, ...]:
        """Gravity per sample, ramped smoothly across posture transitions."""
        cfg = self.cfg.posture
        gx = np.zeros(len(t_ms))
        gy = np.zeros(len(t_ms))
        gz = np.zeros(len(t_ms))
        segs = self.night.postures
        for i, seg in enumerate(segs):
            v = gravity_vector(seg.posture, seg.hob_angle_deg)
            mask = (t_ms >= seg.t_start_ms) & (t_ms < seg.t_end_ms)
            if mask.any():
                gx[mask], gy[mask], gz[mask] = v
            # Ramp into this segment from the previous posture.
            if i > 0 and cfg.transition_ms > 0:
                prev = gravity_vector(segs[i - 1].posture, segs[i - 1].hob_angle_deg)
                tm = (t_ms >= seg.t_start_ms) & (t_ms < seg.t_start_ms + cfg.transition_ms)
                if tm.any():
                    a = ((t_ms[tm] - seg.t_start_ms) / cfg.transition_ms)[:, None]
                    blend = np.array(prev) * (1 - a) + np.array(v) * a
                    gx[tm], gy[tm], gz[tm] = blend[:, 0], blend[:, 1], blend[:, 2]
        if t_ms[-1] >= segs[-1].t_end_ms:
            tail = t_ms >= segs[-1].t_end_ms
            v = gravity_vector(segs[-1].posture, segs[-1].hob_angle_deg)
            gx[tail], gy[tail], gz[tail] = v
        return gx, gy, gz

    def _add_kernels(self, out: dict[str, np.ndarray], t0_ms: int, t1_ms: int) -> None:
        s = self.cfg.signal
        for k in self._kernels:
            k_end = k.t_start_ms + int(len(k.acoustic) / s.acoustic_fs_hz * 1000)
            if k_end < t0_ms or k.t_start_ms > t1_ms:
                continue
            _splice(out["acoustic"], k.acoustic, k.t_start_ms - t0_ms, s.acoustic_fs_hz)
            _splice(out["imu_az"], k.imu_az, k.t_start_ms - t0_ms, s.imu_fs_hz)
            _splice(out["imu_gy"], k.imu_gy, k.t_start_ms - t0_ms, s.imu_fs_hz)
            _splice(out["semg"], k.semg, k.t_start_ms - t0_ms, s.semg_fs_hz)


def _time_grid(t0_ms: int, t1_ms: int, fs: int) -> np.ndarray:
    n = int(round((t1_ms - t0_ms) / 1000.0 * fs))
    return t0_ms + np.arange(n) * (1000.0 / fs)


def _splice(dst: np.ndarray, src: np.ndarray, offset_ms: float, fs: int) -> None:
    start = int(round(offset_ms / 1000.0 * fs))
    a, b = max(0, start), min(len(dst), start + len(src))
    if b <= a:
        return
    dst[a:b] += src[a - start : b - start]


# ----------------------------------------------------------------- kernels
def _build_kernels(cfg: Scenario, night: Night, seed: int) -> list[_Kernel]:
    """One deterministic waveform kernel per swallow, independent of chunking."""
    s = cfg.signal
    out: list[_Kernel] = []
    for i, sw in enumerate(night.swallows):
        rng = np.random.default_rng([seed, 900, i])
        dur_s = (sw.t_end_ms - sw.t_start_ms) / 1000.0
        out.append(
            _Kernel(
                t_start_ms=sw.t_start_ms,
                acoustic=_acoustic_kernel(rng, dur_s, s.acoustic_fs_hz, s.swallow_acoustic_amp),
                imu_az=_imu_kernel(dur_s, s.imu_fs_hz, s.swallow_imu_amp_g),
                imu_gy=_gyro_kernel(dur_s, s.imu_fs_hz, s.swallow_imu_amp_g * 900.0),
                semg=_semg_kernel(rng, dur_s, s.semg_fs_hz, s.swallow_semg_amp_uv),
            )
        )
    return out


def _acoustic_kernel(rng, dur_s: float, fs: int, amp: float) -> np.ndarray:
    """Three-phase swallow sound: oral squeeze, pharyngeal burst, oesophageal tail."""
    n = int(dur_s * fs)
    t = np.arange(n) / fs
    out = np.zeros(n)
    phases = [
        (0.00, 0.15, 80, 350, 0.30),  # oral: tongue driving the bolus back
        (0.15, 0.45, 350, 1800, 1.00),  # pharyngeal: the click, highest energy
        (0.45, 1.00, 100, 600, 0.40),  # oesophageal: low tail
    ]
    for a, b, lo, hi, gain in phases:
        i0, i1 = int(a * n), int(b * n)
        if i1 - i0 < 8:
            continue
        seg = rng.standard_normal(i1 - i0)
        sos = sps.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
        seg = sps.sosfiltfilt(sos, seg)
        env = np.hanning(len(seg))
        out[i0:i1] += gain * seg / (np.max(np.abs(seg)) + 1e-12) * env
    out *= amp / (np.max(np.abs(out)) + 1e-12)
    # Short fade so splicing never introduces a step.
    return out * _fade(n, int(0.005 * fs)) if n else out


def _imu_kernel(dur_s: float, fs: int, amp: float) -> np.ndarray:
    """Hyoid-laryngeal excursion: a rise then a slightly slower fall on the S-I axis."""
    n = max(4, int((dur_s + 0.2) * fs))
    t = np.arange(n) / fs
    up = np.exp(-(((t - 0.18 * dur_s / 0.9) / (0.09 * dur_s / 0.9)) ** 2))
    down = np.exp(-(((t - 0.55 * dur_s / 0.9) / (0.11 * dur_s / 0.9)) ** 2))
    k = up - 0.85 * down
    return amp * k / (np.max(np.abs(k)) + 1e-12)


def _gyro_kernel(dur_s: float, fs: int, amp: float) -> np.ndarray:
    k = _imu_kernel(dur_s, fs, 1.0)
    d = np.gradient(k)
    return amp * d / (np.max(np.abs(d)) + 1e-12)


def _semg_kernel(rng, dur_s: float, fs: int, rms_uv: float) -> np.ndarray:
    """Submental burst: onset leads the acoustic signature, offset precedes its tail."""
    n = int(dur_s * fs)
    if n < 16:
        return np.zeros(max(n, 0))
    i0, i1 = int(0.05 * n), int(0.75 * n)
    burst = rng.standard_normal(i1 - i0)
    sos = sps.butter(4, [20, 450], btype="bandpass", fs=fs, output="sos")
    burst = sps.sosfiltfilt(sos, burst)
    burst *= rms_uv / (np.std(burst) + 1e-12)
    env = 0.5 * (1 - np.cos(2 * np.pi * np.arange(len(burst)) / max(1, len(burst) - 1)))
    out = np.zeros(n)
    out[i0:i1] = burst * env
    return out


def _fade(n: int, k: int) -> np.ndarray:
    w = np.ones(n)
    k = min(k, n // 2)
    if k > 0:
        ramp = np.linspace(0, 1, k)
        w[:k] = ramp
        w[-k:] = ramp[::-1]
    return w
