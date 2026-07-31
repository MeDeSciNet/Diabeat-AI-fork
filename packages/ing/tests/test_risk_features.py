"""Feature extraction and the overnight signal index."""

from __future__ import annotations

import numpy as np
import pytest

from somno_ing import features as F
from somno_ing import risk as R
from somno_ing.detect import DERIVED_FS, Derived
from somno_ing.detect.base import DetectedEvent


def _blank(seconds: int = 600) -> Derived:
    n = int(seconds * DERIVED_FS)
    d = Derived()
    for name in Derived.ARRAYS:
        setattr(d, name, np.zeros(n, dtype=np.float32))
    d.present = np.ones(n, bool)
    d.semg_ok = np.ones(n, bool)
    d.gated = np.zeros(n, bool)
    d.snoring = np.zeros(n, bool)
    d.gx = np.full(n, -1.0, np.float32)  # supine, flat
    return d


# ---------------------------------------------------------------- posture
@pytest.mark.parametrize(
    "vector,expected",
    [
        ((-1, 0, 0), "supine"),
        ((1, 0, 0), "prone"),
        ((0, -1, 0), "left"),
        ((0, 1, 0), "right"),
        ((0, 0, -1), "upright"),
    ],
)
def test_posture_is_recovered_from_gravity(vector, expected):
    posture, _ = F.posture_from_gravity(*vector)
    assert posture == expected


def test_head_of_bed_angle_is_recovered():
    from somno_sim.signals import gravity_vector

    for target in (0.0, 10.0, 30.0, 45.0):
        posture, hob = F.posture_from_gravity(*gravity_vector("supine", target))
        assert posture == "supine"
        assert hob == pytest.approx(target, abs=1.0)


def test_posture_segments_absorb_short_flickers():
    d = _blank(1200)
    n = len(d)
    d.gx[:] = -1.0
    d.gy[:] = 0.0
    # A two-second glitch to the left side must not become a segment.
    a, b = int(600 * DERIVED_FS), int(602 * DERIVED_FS)
    d.gx[a:b] = 0.0
    d.gy[a:b] = -1.0
    segs = F.posture_segments(d)
    assert len(segs) == 1 and segs[0]["posture"] == "supine"
    assert segs[0]["t_end_ms"] == pytest.approx(n / DERIVED_FS * 1000, abs=100)


# ----------------------------------------------------------- coordination
def _respiration(d: Derived, rate_per_min: float = 14.0) -> None:
    t = np.arange(len(d)) / d.fs
    phi = rate_per_min / 60.0 * t
    d.resp_volume = (0.5 * (1 - np.cos(2 * np.pi * phi))).astype(np.float32)


def test_respiratory_phase_is_read_off_the_volume_slope():
    d = _blank(120)
    _respiration(d)
    slope, scale = F._slope(d)
    period = 60.0 / 14.0
    # A quarter period in is mid-inspiration; three quarters is mid-expiration.
    insp_ms = 0.25 * period * 1000
    exp_ms = 0.75 * period * 1000
    assert F._phase_of(slope, scale, d, insp_ms - 200, insp_ms + 200) == "I"
    assert F._phase_of(slope, scale, d, exp_ms - 200, exp_ms + 200) == "E"


def test_coordination_accuracy_on_a_real_night(analysed_session):
    """Recovered pattern must agree with ground truth well above chance (25%)."""
    acc = analysed_session["eval"]["coordination_accuracy"]
    assert acc is not None and acc >= 0.6, f"coordination accuracy {acc}"


def test_swallow_followed_by_inspiration_counts_as_anomalous():
    d = _blank(60)
    events = [DetectedEvent(1000, 1900, 0.9, {})]
    anns = [
        F.EventAnnotation(coordination_pattern="E-E"),
        F.EventAnnotation(coordination_pattern="E-I"),
        F.EventAnnotation(coordination_pattern="I-I"),
        F.EventAnnotation(coordination_pattern="I-E"),
    ]
    feats = F.compute(events * 4, anns, d, [])
    assert feats.coordination_anomaly == pytest.approx(0.5)


# ------------------------------------------------------------------- SFI
def test_sfi_burden_counts_time_inside_long_gaps():
    d = _blank(3600)
    # Two events an hour apart: nearly the whole hour is one long interval.
    events = [DetectedEvent(0, 900, 0.9, {}), DetectedEvent(3_500_000, 3_500_900, 0.9, {})]
    feats = F.compute(events, [F.EventAnnotation()] * 2, d, [], sfi_reference_s=600.0)
    assert feats.sfi_max_s > 3000
    assert feats.sfi_burden > 0.9


def test_short_intervals_do_not_count_towards_burden():
    d = _blank(600)
    events = [DetectedEvent(i * 60_000, i * 60_000 + 900, 0.9, {}) for i in range(10)]
    feats = F.compute(events, [F.EventAnnotation()] * 10, d, [], sfi_reference_s=600.0)
    assert feats.sfi_burden == 0.0


# --------------------------------------------------------------- supine
def test_supine_burden_needs_both_supine_and_a_low_head_of_bed():
    from somno_sim.signals import gravity_vector

    d = _blank(600)
    gx, gy, gz = gravity_vector("supine", 40.0)
    d.gx[:], d.gy[:], d.gz[:] = gx, gy, gz
    feats = F.compute([], [], d, [])
    assert feats.posture_ratios["supine"] == pytest.approx(1.0)
    assert feats.supine_burden == 0.0  # head of bed is up, so no burden

    d.gx[:], d.gy[:], d.gz[:] = gravity_vector("supine", 0.0)
    feats = F.compute([], [], d, [])
    assert feats.supine_burden == pytest.approx(1.0)


# ----------------------------------------------------------------- risk
def _features(**over) -> F.NightFeatures:
    f = F.NightFeatures(n_events=60, arousal_coupling=0.7)
    for k, v in over.items():
        setattr(f, k, v)
    return f


def test_bands_follow_the_configured_edges():
    cfg = R.RiskConfig()
    low = R.score(_features(), R.DataQuality(1.0, 0.0), cfg)
    assert low["band"] == "low" and low["score"] == 0.0

    high = R.score(
        _features(
            sfi_burden=1.0, coordination_anomaly=1.0, supine_burden=1.0, arousal_coupling=0.0
        ),
        R.DataQuality(1.0, 0.0),
        cfg,
    )
    assert high["band"] == "elevated" and high["score"] == 100.0


def test_insufficient_coverage_yields_no_score():
    out = R.score(_features(), R.DataQuality(signal_coverage=0.4, artifact_ratio=0.05))
    assert out["band"] == "insufficient_data" and out["score"] is None


def test_excess_artifact_yields_no_score():
    out = R.score(_features(), R.DataQuality(signal_coverage=0.95, artifact_ratio=0.55))
    assert out["band"] == "insufficient_data" and out["score"] is None


def test_component_weights_sum_to_one():
    cfg = R.RiskConfig()
    assert sum(c["weight"] for c in cfg.components.values()) == pytest.approx(1.0)


def test_arousal_decoupling_measures_shortfall_below_the_literature_floor():
    cfg = R.RiskConfig()
    normal = R.raw_components(_features(arousal_coupling=0.70), cfg)
    assert normal["arousal_decoupling"] == 0.0
    decoupled = R.raw_components(_features(arousal_coupling=0.10), cfg)
    assert decoupled["arousal_decoupling"] > 0.7


def test_too_few_events_makes_decoupling_unmeasurable_not_maximal():
    """A near-empty night must not score as maximally decoupled."""
    cfg = R.RiskConfig()
    sparse = R.raw_components(_features(n_events=2, arousal_coupling=0.0), cfg)
    assert sparse["arousal_decoupling"] == 0.0


def test_algorithm_version_is_reported_and_versioned():
    out = R.score(_features(), R.DataQuality(1.0, 0.0))
    assert out["algorithm_version"].startswith("risk-v")


def test_analysis_is_idempotent(analysed_session):
    """PRD 10.3: re-running a session must produce the same result."""
    from somno_ing.pipeline import analyze

    first = analysed_session["analysis"]
    second = analyze(analysed_session["session_id"])
    assert second["risk"] == first["risk"]
    assert second["features"] == first["features"]
    assert second["n_events"] == first["n_events"]
