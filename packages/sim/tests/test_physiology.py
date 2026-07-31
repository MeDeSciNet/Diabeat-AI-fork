"""Physiology layer against the PRD 5.3 acceptance criteria."""

import numpy as np
import pytest

from somno_sim.config import available_scenarios, load_scenario
from somno_sim.physiology import EPOCH_MS, build_night


@pytest.mark.parametrize("seed", [1, 42, 99, 2024])
def test_healthy_adult_whole_night_swallow_count(seed):
    """PRD 5.3: a full healthy night lands in 60-140 swallows."""
    cfg = load_scenario("healthy_adult")
    night = build_night(cfg, seed)
    assert 60 <= len(night.swallows) <= 140, f"seed {seed} produced {len(night.swallows)}"


@pytest.mark.parametrize("scenario", ["healthy_adult", "elderly_high_risk", "post_stroke"])
def test_arousal_coupling_within_3_percent(scenario):
    """PRD 5.3: realised coupling must track the configured ratio to within 3%."""
    cfg = load_scenario(scenario)
    night = build_night(cfg, 42)
    linked = sum(1 for s in night.swallows if s.arousal_linked)
    actual = linked / len(night.swallows)
    target = cfg.swallow.arousal_coupling_ratio
    assert abs(actual - target) < 0.03, f"{scenario}: {actual:.3f} vs {target}"


def test_sleep_stage_ratios_track_configuration():
    cfg = load_scenario("healthy_adult")
    night = build_night(cfg, 42)
    total = len(night.hypnogram)
    for stage, target in cfg.sleep.stage_ratios.items():
        actual = night.hypnogram.count(stage) / total
        assert abs(actual - target) < 0.06, f"{stage}: {actual:.3f} vs {target}"


def test_rem_is_weighted_towards_the_second_half():
    night = build_night(load_scenario("healthy_adult"), 42)
    half = len(night.hypnogram) // 2
    first = night.hypnogram[:half].count("REM")
    second = night.hypnogram[half:].count("REM")
    assert second > first


def test_n3_is_weighted_towards_the_first_half():
    night = build_night(load_scenario("healthy_adult"), 42)
    half = len(night.hypnogram) // 2
    assert night.hypnogram[:half].count("N3") > night.hypnogram[half:].count("N3")


def test_arousal_index_matches_configuration():
    cfg = load_scenario("healthy_adult")
    night = build_night(cfg, 42)
    hours = cfg.duration_ms / 3_600_000
    # The 20 s merge rule removes a few, so allow a downward margin only.
    assert 0.75 * cfg.sleep.arousal_index <= len(night.arousals) / hours <= cfg.sleep.arousal_index * 1.05


def test_coordination_distribution_is_respected():
    cfg = load_scenario("elderly_high_risk")
    night = build_night(cfg, 42)
    counts = {}
    for s in night.swallows:
        counts[s.coordination_pattern] = counts.get(s.coordination_pattern, 0) + 1
    n = len(night.swallows)
    for pattern, target in cfg.swallow.coordination_distribution.items():
        assert abs(counts.get(pattern, 0) / n - target) < 0.12, pattern


def test_respiratory_phase_matches_each_swallows_pattern():
    """The pattern is rendered into the phase timeline, not just annotated."""
    cfg = load_scenario("elderly_high_risk")
    night = build_night(cfg, 42)
    for sw in night.swallows[:40]:
        phi_before = night.resp_phase(np.array([float(sw.t_start_ms)]))[0]
        expected = "I" if phi_before < 0.5 else "E"
        assert expected == sw.resp_phase_before
        after_t = sw.t_start_ms + sw.swallow_apnea_ms + 1
        phi_after = night.resp_phase(np.array([float(after_t)]))[0]
        assert ("I" if phi_after < 0.5 else "E") == sw.resp_phase_after


def test_lung_volume_is_continuous_across_the_apnea():
    """A phase reset must not put a step into the respiration signal."""
    night = build_night(load_scenario("healthy_adult").model_copy(update={"duration_min": 60}), 42)
    for sw in night.swallows:
        t0 = float(sw.t_start_ms)
        t1 = float(sw.t_start_ms + sw.swallow_apnea_ms)
        v0 = 0.5 * (1 - np.cos(2 * np.pi * night.resp_phase(np.array([t0]))[0]))
        v1 = 0.5 * (1 - np.cos(2 * np.pi * night.resp_phase(np.array([t1 + 1]))[0]))
        assert abs(v0 - v1) < 0.02


def test_swallows_respect_the_minimum_interval():
    cfg = load_scenario("healthy_adult")
    night = build_night(cfg, 42)
    times = [s.t_start_ms for s in night.swallows]
    # The respiratory-phase nudge can shift an onset by up to one breath.
    breath_ms = 60_000 / cfg.resp.rate_per_min
    for a, b in zip(times, times[1:]):
        assert b - a > cfg.swallow.min_interval_ms - breath_ms


def test_posture_ratios_track_configuration():
    cfg = load_scenario("elderly_high_risk")
    night = build_night(cfg, 42)
    total = sum(p.t_end_ms - p.t_start_ms for p in night.postures)
    supine = sum(p.t_end_ms - p.t_start_ms for p in night.postures if p.posture == "supine")
    assert supine / total > 0.5


@pytest.mark.parametrize("scenario", available_scenarios())
def test_every_scenario_builds_a_full_night(scenario):
    cfg = load_scenario(scenario)
    night = build_night(cfg, 3)
    assert len(night.hypnogram) == cfg.duration_ms // EPOCH_MS
    assert night.swallows
    assert night.postures[-1].t_end_ms == cfg.duration_ms
