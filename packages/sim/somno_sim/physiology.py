"""Physiology layer: builds the night before any waveform exists.

Order of construction matters, because each layer constrains the next:

    sleep architecture -> arousals -> swallow times -> respiration -> posture

Respiration comes after swallow times because each swallow's assigned
coordination pattern (E-E, E-I, ...) is *rendered into* the respiratory phase
timeline. That is what lets ING recover the pattern from the signal rather than
being told it.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field

import numpy as np

from .config import Scenario
from .rng import effective_seed, stream

EPOCH_MS = 30_000
STAGE_AROUSAL_WEIGHT = {"W": 0.0, "N1": 1.5, "N2": 1.0, "N3": 0.3, "REM": 1.2}

# Phase convention: phi in [0,1). Lung volume V(phi) = 0.5*(1-cos(2*pi*phi)),
# so phi in (0,0.5) is inspiration (volume rising) and (0.5,1) is expiration.
PHASE_BAND = {"I": (0.10, 0.40), "E": (0.60, 0.90)}


@dataclass
class Arousal:
    id: str
    t_start_ms: int
    duration_ms: int


@dataclass
class PostureSeg:
    t_start_ms: int
    t_end_ms: int
    posture: str
    hob_angle_deg: float


@dataclass
class RespSeg:
    """Respiration is piecewise: a new segment starts after every swallow apnea."""

    t0_ms: int
    phi0: float
    f_hz: float


@dataclass
class Swallow:
    id: str
    t_start_ms: int
    t_end_ms: int
    sleep_stage: str
    arousal_linked: bool
    arousal_id: str | None
    coordination_pattern: str
    resp_phase_before: str
    resp_phase_after: str
    swallow_apnea_ms: int
    posture: str
    hob_angle_deg: float | None


@dataclass
class Night:
    duration_ms: int
    hypnogram: list[str]
    arousals: list[Arousal]
    postures: list[PostureSeg]
    resp_segments: list[RespSeg] = field(default_factory=list)
    swallows: list[Swallow] = field(default_factory=list)

    def stage_at(self, t_ms: float) -> str:
        idx = int(t_ms // EPOCH_MS)
        if 0 <= idx < len(self.hypnogram):
            return self.hypnogram[idx]
        return "W"

    def posture_at(self, t_ms: float) -> PostureSeg:
        for seg in self.postures:
            if seg.t_start_ms <= t_ms < seg.t_end_ms:
                return seg
        return self.postures[-1]

    def resp_phase(self, t_ms: np.ndarray) -> np.ndarray:
        """Vectorised phase lookup across the piecewise respiration timeline."""
        t0 = np.array([s.t0_ms for s in self.resp_segments], dtype=np.float64)
        phi0 = np.array([s.phi0 for s in self.resp_segments])
        f = np.array([s.f_hz for s in self.resp_segments])
        idx = np.clip(np.searchsorted(t0, t_ms, side="right") - 1, 0, len(t0) - 1)
        return np.mod(phi0[idx] + f[idx] * (t_ms - t0[idx]) / 1000.0, 1.0)

    def apnea_mask(self, t_ms: np.ndarray) -> np.ndarray:
        """True where respiration is held by a swallow apnea."""
        mask = np.zeros_like(t_ms, dtype=bool)
        for sw in self.swallows:
            mask |= (t_ms >= sw.t_start_ms) & (t_ms < sw.t_start_ms + sw.swallow_apnea_ms)
        return mask


def build_night(cfg: Scenario, seed: int) -> Night:
    seed = effective_seed(seed, cfg.scenario)
    hypnogram = _build_hypnogram(cfg, stream(seed, "sleep"))
    arousals = _build_arousals(cfg, hypnogram, stream(seed, "arousal"))
    postures = _build_postures(cfg, stream(seed, "posture"))
    night = Night(
        duration_ms=cfg.duration_ms,
        hypnogram=hypnogram,
        arousals=arousals,
        postures=postures,
    )
    times, links = _swallow_times(cfg, night, stream(seed, "swallow"))
    _build_respiration(cfg, night, times, links, stream(seed, "resp"))
    return night


# --------------------------------------------------------------------- sleep
def _build_hypnogram(cfg: Scenario, rng: np.random.Generator) -> list[str]:
    n_epochs = max(1, cfg.duration_ms // EPOCH_MS)
    lead = min(int(cfg.sleep.sleep_onset_min * 2), n_epochs)
    sleep_epochs = n_epochs - lead
    if sleep_epochs <= 0:
        return ["W"] * n_epochs

    ratios = cfg.sleep.stage_ratios
    total_ratio = sum(ratios.values()) or 1.0
    targets = _largest_remainder(
        {s: ratios.get(s, 0.0) / total_ratio for s in ("N1", "N2", "N3", "REM")}, sleep_epochs
    )

    n_cycles = max(1, int(round(cfg.duration_min / cfg.sleep.cycle_min)))
    # REM grows across the night; N3 is front-loaded. Classic adult architecture.
    rem_w = np.arange(1, n_cycles + 1, dtype=float)
    n3_w = np.arange(n_cycles, 0, -1, dtype=float)
    flat = np.ones(n_cycles)
    per_cycle = {
        "REM": _split(targets["REM"], rem_w),
        "N3": _split(targets["N3"], n3_w),
        "N1": _split(targets["N1"], flat),
        "N2": _split(targets["N2"], flat),
    }

    out: list[str] = ["W"] * lead
    for c in range(n_cycles):
        n1, n2, n3, rem = (per_cycle[s][c] for s in ("N1", "N2", "N3", "REM"))
        n2_a, n2_b = n2 - n2 // 2, n2 // 2
        out += ["N1"] * n1 + ["N2"] * n2_a + ["N3"] * n3 + ["N2"] * n2_b + ["REM"] * rem
        # A brief awakening at the cycle boundary, as normally seen after REM.
        if c < n_cycles - 1 and rng.random() < 0.5 and len(out) < n_epochs:
            out.append("W")
    out = out[:n_epochs]
    out += ["W"] * (n_epochs - len(out))
    return out


def _split(total: int, weights: np.ndarray) -> list[int]:
    w = weights / weights.sum()
    return list(_largest_remainder({i: w[i] for i in range(len(w))}, total).values())


def _largest_remainder(shares: dict, total: int) -> dict:
    raw = {k: v * total for k, v in shares.items()}
    out = {k: int(math.floor(v)) for k, v in raw.items()}
    remainder = total - sum(out.values())
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[:remainder]:
        out[k] += 1
    return out


# ------------------------------------------------------------------ arousals
def _build_arousals(
    cfg: Scenario, hypnogram: list[str], rng: np.random.Generator
) -> list[Arousal]:
    hours = cfg.duration_ms / 3_600_000
    n = int(round(cfg.sleep.arousal_index * hours))
    if n <= 0:
        return []
    weights = np.array([STAGE_AROUSAL_WEIGHT[s] for s in hypnogram])
    if weights.sum() == 0:
        return []
    weights = weights / weights.sum()
    epochs = rng.choice(len(hypnogram), size=n, p=weights, replace=True)
    times = np.sort(epochs * EPOCH_MS + rng.uniform(0, EPOCH_MS, size=n))

    out: list[Arousal] = []
    last = -1e9
    for t in times:
        if t - last < 20_000:  # arousals closer than 20 s are one arousal
            continue
        last = t
        dur = float(
            np.clip(
                rng.normal(cfg.sleep.arousal_duration_ms.mean, cfg.sleep.arousal_duration_ms.sd),
                3_000,
                30_000,
            )
        )
        out.append(
            Arousal(id=_uuid(rng), t_start_ms=int(t), duration_ms=int(dur))
        )
    return out


# ------------------------------------------------------------------ postures
def _build_postures(cfg: Scenario, rng: np.random.Generator) -> list[PostureSeg]:
    hours = cfg.duration_ms / 3_600_000
    n_turns = int(round(cfg.posture.turns_per_hour * hours))
    edges = [0]
    if n_turns > 0:
        cand = np.sort(rng.uniform(0, cfg.duration_ms, size=n_turns))
        for t in cand:
            if t - edges[-1] >= 300_000:  # no segment shorter than 5 minutes
                edges.append(int(t))
    edges.append(cfg.duration_ms)

    names = list(cfg.posture.ratios)
    probs = np.array([cfg.posture.ratios[k] for k in names])
    probs = probs / probs.sum()

    segs: list[PostureSeg] = []
    prev = None
    for a, b in zip(edges[:-1], edges[1:]):
        choice = names[int(rng.choice(len(names), p=probs))]
        for _ in range(4):  # a turn that lands on the same posture is not a turn
            if choice != prev:
                break
            choice = names[int(rng.choice(len(names), p=probs))]
        prev = choice
        segs.append(
            PostureSeg(
                t_start_ms=a, t_end_ms=b, posture=choice, hob_angle_deg=cfg.posture.hob_angle_deg
            )
        )
    return segs


# ------------------------------------------------------------------ swallows
def _swallow_times(
    cfg: Scenario, night: Night, rng: np.random.Generator
) -> tuple[list[float], list[str | None]]:
    """Return swallow onset times and, for each, the arousal id it is coupled to."""
    sc = cfg.swallow
    # Per-night rate for this subject: literature mean, literature spread.
    rates = {}
    for stage in ("N1", "N2", "N3", "REM"):
        mean = sc.rates_per_hour.get(stage, 0.0)
        sd = sc.rate_sd_per_hour.get(stage, 0.0)
        rates[stage] = max(0.0, float(rng.normal(mean, sd))) * sc.rate_scale
    rates["W"] = rates.get("N1", 0.0)  # wake swallowing resembles light sleep here

    per_epoch = np.array([rates.get(s, 0.0) / 3600.0 * (EPOCH_MS / 1000.0) for s in night.hypnogram])
    expected = per_epoch.sum()
    n_total = int(rng.poisson(expected))
    if n_total == 0:
        return [], []

    n_coupled = int(round(n_total * sc.arousal_coupling_ratio))
    if not night.arousals:
        n_coupled = 0
    n_free = n_total - n_coupled

    times: list[float] = []
    links: list[str | None] = []

    # Coupled: anchored within +/- arousal_window_ms of an arousal onset.
    if n_coupled:
        order = rng.permutation(len(night.arousals))
        for i in range(n_coupled):
            ar = night.arousals[int(order[i % len(order)])]
            t = ar.t_start_ms + rng.uniform(-sc.arousal_window_ms, sc.arousal_window_ms)
            times.append(float(np.clip(t, 0, cfg.duration_ms - 2000)))
            links.append(ar.id)

    # Free: drawn from the stage-rate intensity, and explicitly kept *out* of
    # arousal windows so arousal_coupling_ratio means exactly what it says.
    if n_free:
        cdf = np.cumsum(per_epoch)
        if cdf[-1] <= 0:
            cdf = np.arange(1, len(per_epoch) + 1, dtype=float)
        cdf = cdf / cdf[-1]
        windows = np.array(
            [[a.t_start_ms - sc.arousal_window_ms, a.t_start_ms + sc.arousal_window_ms] for a in night.arousals]
        ) if night.arousals else np.zeros((0, 2))
        placed = 0
        for _ in range(n_free * 50):
            if placed >= n_free:
                break
            e = int(np.searchsorted(cdf, rng.random()))
            t = min(e, len(per_epoch) - 1) * EPOCH_MS + rng.uniform(0, EPOCH_MS)
            if len(windows) and np.any((t >= windows[:, 0]) & (t <= windows[:, 1])):
                continue
            times.append(float(np.clip(t, 0, cfg.duration_ms - 2000)))
            links.append(None)
            placed += 1

    order = np.argsort(times)
    times = [times[i] for i in order]
    links = [links[i] for i in order]

    kept_t: list[float] = []
    kept_l: list[str | None] = []
    for t, link in zip(times, links):
        if kept_t and t - kept_t[-1] < sc.min_interval_ms:
            continue
        kept_t.append(t)
        kept_l.append(link)
    return kept_t, kept_l


# -------------------------------------------------------------- respiration
def _build_respiration(
    cfg: Scenario,
    night: Night,
    times: list[float],
    links: list[str | None],
    rng: np.random.Generator,
) -> None:
    """Lay down the respiratory phase timeline and finalise the swallow events.

    Each swallow is nudged (by less than one breath) onto a respiratory phase
    matching its assigned pattern's leading phase, then the phase resumes after
    the apnea at whichever point in the target half-cycle keeps lung volume
    continuous. The result: the coordination pattern is genuinely present in the
    signal, not merely annotated.
    """
    f0 = cfg.resp.rate_per_min / 60.0
    patterns = list(cfg.swallow.coordination_distribution)
    probs = np.array([cfg.swallow.coordination_distribution[p] for p in patterns])
    probs = probs / probs.sum()

    def jittered_f() -> float:
        return max(
            0.08,
            float(rng.normal(f0, cfg.resp.rate_sd_per_min / 60.0)),
        )

    night.resp_segments = [RespSeg(t0_ms=0, phi0=float(rng.random()), f_hz=jittered_f())]

    for t_raw, link in zip(times, links):
        seg = night.resp_segments[-1]
        pattern = patterns[int(rng.choice(len(patterns), p=probs))]
        before, after = pattern.split("-")
        lo, hi = PHASE_BAND[before]

        # Advance to the next instant whose phase sits in the target band.
        t = max(float(t_raw), seg.t0_ms + 1.0)
        phi = math.fmod(seg.phi0 + seg.f_hz * (t - seg.t0_ms) / 1000.0, 1.0)
        target = lo + (hi - lo) * rng.random()
        delta = (target - phi) % 1.0
        t += delta / seg.f_hz * 1000.0
        if t >= night.duration_ms - 2000:
            continue
        phi_s = target

        apnea = int(np.clip(rng.normal(cfg.swallow.apnea_ms.mean, cfg.swallow.apnea_ms.sd), 300, 3000))
        dur = int(np.clip(rng.normal(cfg.swallow.duration_ms.mean, cfg.swallow.duration_ms.sd), 350, 2000))

        # Resume at the phase in the target half with the same lung volume, so
        # volume stays continuous and only its slope flips.
        vol = 0.5 * (1.0 - math.cos(2 * math.pi * phi_s))
        phi_i = math.acos(max(-1.0, min(1.0, 1.0 - 2.0 * vol))) / (2 * math.pi)
        phi_after = phi_i if after == "I" else 1.0 - phi_i
        night.resp_segments.append(
            RespSeg(t0_ms=int(t + apnea), phi0=float(phi_after), f_hz=jittered_f())
        )

        posture = night.posture_at(t)
        night.swallows.append(
            Swallow(
                id=_uuid(rng),
                t_start_ms=int(t),
                t_end_ms=int(t + dur),
                sleep_stage=night.stage_at(t),
                arousal_linked=link is not None,
                arousal_id=link,
                coordination_pattern=pattern,
                resp_phase_before=before,
                resp_phase_after=after,
                swallow_apnea_ms=apnea,
                posture=posture.posture,
                hob_angle_deg=posture.hob_angle_deg,
            )
        )


def _uuid(rng: np.random.Generator) -> str:
    """Deterministic UUIDv4 drawn from the scenario's RNG stream."""
    return str(uuid.UUID(bytes=rng.bytes(16), version=4))
