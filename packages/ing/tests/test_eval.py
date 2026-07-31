"""Event matching and the detection report."""

from __future__ import annotations

import pytest

from somno_ing.eval import match_events, report


def ev(t: int, dur: int = 900, **extra) -> dict:
    return {"t_start_ms": t, "t_end_ms": t + dur, **extra}


def test_perfect_agreement():
    gt = [ev(1000), ev(5000), ev(9000)]
    out = report("s", gt, list(gt))
    assert (out["precision"], out["recall"], out["f1"]) == (1.0, 1.0, 1.0)
    assert out["onset_error_ms"]["max"] == 0.0


def test_a_near_miss_inside_tolerance_counts_as_a_hit():
    gt = [ev(1000)]
    detected = [ev(1400)]
    matches, missed, extra = match_events(gt, detected, tolerance_ms=750)
    assert len(matches) == 1 and not missed and not extra
    assert matches[0].onset_error_ms == 400


def test_a_miss_outside_tolerance_counts_as_both_errors():
    matches, missed, extra = match_events([ev(1000)], [ev(3000)], tolerance_ms=750)
    assert not matches and missed == [0] and extra == [0]


def test_each_event_matches_at_most_once():
    """Two detections near one true event must not both be credited."""
    gt = [ev(1000)]
    detected = [ev(1050), ev(1200)]
    out = report("s", gt, detected)
    assert out["true_positives"] == 1
    assert out["false_positives"] == 1
    assert out["precision"] == 0.5 and out["recall"] == 1.0


def test_nearest_detection_wins():
    matches, _, _ = match_events([ev(1000)], [ev(1600), ev(1050)], tolerance_ms=750)
    assert len(matches) == 1 and matches[0].det_index == 1


def test_empty_inputs_do_not_divide_by_zero():
    out = report("s", [], [])
    assert out["f1"] == 0.0 and out["coordination_accuracy"] is None


def test_per_stage_recall_is_broken_out():
    gt = [ev(1000, sleep_stage="N2"), ev(5000, sleep_stage="N2"), ev(9000, sleep_stage="REM")]
    detected = [ev(1000), ev(5000)]
    out = report("s", gt, detected)
    assert out["by_sleep_stage"]["N2"] == {"n_ground_truth": 2, "recall": 1.0}
    assert out["by_sleep_stage"]["REM"] == {"n_ground_truth": 1, "recall": 0.0}


def test_coordination_accuracy_counts_only_matched_events():
    gt = [ev(1000, coordination_pattern="E-E"), ev(5000, coordination_pattern="E-I")]
    detected = [ev(1000, coordination_pattern="E-E"), ev(5000, coordination_pattern="E-E")]
    out = report("s", gt, detected)
    assert out["coordination_accuracy"] == pytest.approx(0.5)
