"""Detection accuracy against SIM ground truth (PRD milestone M2)."""

from __future__ import annotations

import numpy as np
import pytest

from somno_ing.detect import Derived
from somno_ing.detect.candidates import CandidateConfig, biphasic_template, imu_candidates
from somno_ing.detect.fusion import FusionConfig, fuse
from somno_ing.detect.base import Candidate
from somno_ing.devtools import run_scenario

# The PRD milestone targets. Runs use a shortened night so the suite stays
# usable; the detector is duration-independent.
TARGETS = {"healthy_adult": 0.85, "noisy_signal": 0.70}


@pytest.mark.parametrize("scenario,target", sorted(TARGETS.items()))
def test_f1_meets_the_milestone_target(scenario, target):
    # A distinct device id per test: session ids are uuid5(scenario, seed,
    # device), so two tests sharing all three would deterministically collide on
    # one session and overwrite each other's results.
    res = run_scenario(
        scenario=scenario,
        seed=42,
        duration_min=120.0,
        subject_code=f"F1-{scenario}",
        device_id=f"dev-f1-{scenario}",
        bed_id=None,
    )
    ev = res["eval"]
    assert ev["n_ground_truth"] >= 10, "not enough events for the score to mean anything"
    assert ev["f1"] >= target, f"{scenario}: F1 {ev['f1']} below {target}"


def test_onset_timing_is_tight(analysed_session):
    """Onset error must stay well inside the fusion tolerance."""
    assert analysed_session["eval"]["onset_error_ms"]["p90"] <= 300


def test_detected_events_carry_multi_modal_votes(analysed_session):
    from sqlalchemy import select

    from somno_ing.db import SwallowEventRow, db_session

    with db_session() as db:
        rows = db.scalars(
            select(SwallowEventRow).where(
                SwallowEventRow.session_id == analysed_session["session_id"],
                SwallowEventRow.source == "detected",
            )
        ).all()
    assert rows
    for r in rows:
        assert len(r.modality_votes) >= 2, "an event carried by a single modality"
        assert 0.0 <= r.confidence <= 1.0


def test_a_single_modality_cannot_carry_an_event():
    """Structural guard: snoring is acoustic-only, restlessness is IMU-only."""
    d = Derived()
    n = 6000
    for name in Derived.ARRAYS:
        setattr(d, name, np.zeros(n, dtype=np.float32))
    d.present = np.ones(n, bool)
    d.semg_ok = np.ones(n, bool)
    d.gated = np.zeros(n, bool)
    d.snoring = np.zeros(n, bool)

    cfg = FusionConfig()
    only_acoustic = [Candidate("acoustic", 1000, 1900, 1.0)]
    assert fuse(only_acoustic, d, cfg) == []

    two = [Candidate("acoustic", 1000, 1900, 1.0), Candidate("imu", 1050, 1950, 0.9)]
    assert len(fuse(two, d, cfg)) == 1


def test_fusion_renormalises_when_a_modality_is_unavailable():
    """A lost sEMG electrode must not silently fail every later confidence check."""
    n = 6000
    d = Derived()
    for name in Derived.ARRAYS:
        setattr(d, name, np.zeros(n, dtype=np.float32))
    d.present = np.ones(n, bool)
    d.semg_ok = np.zeros(n, bool)  # electrode off for the whole window
    d.gated = np.zeros(n, bool)
    d.snoring = np.zeros(n, bool)

    cands = [Candidate("acoustic", 1000, 1900, 0.8), Candidate("imu", 1050, 1950, 0.8)]
    events = fuse(cands, d, FusionConfig())
    assert len(events) == 1
    assert set(events[0].modality_votes) == {"acoustic", "imu"}
    assert events[0].confidence == pytest.approx(0.8, abs=1e-6)


def test_imu_template_matches_a_synthetic_excursion():
    fs = 100.0
    n = 3000
    d = Derived()
    for name in Derived.ARRAYS:
        setattr(d, name, np.zeros(n, dtype=np.float32))
    d.present = np.ones(n, bool)
    d.semg_ok = np.ones(n, bool)
    d.gated = np.zeros(n, bool)
    d.snoring = np.zeros(n, bool)

    tpl = biphasic_template(900.0, fs)
    at = 1500
    d.imu_si[at : at + len(tpl)] = (tpl * 0.05).astype(np.float32)

    found = imu_candidates(d, CandidateConfig())
    assert found, "template match found nothing"
    centres = [c.t_center_ms for c in found]
    assert min(abs(c - (at / fs * 1000 + 450)) for c in centres) < 300


def test_sensor_failure_night_still_detects_after_the_electrode_drops():
    res = run_scenario(
        scenario="sensor_failure",
        seed=42,
        duration_min=300.0,
        subject_code="SUBJ-DETACH",
        device_id="dev-detach",
        bed_id=None,
    )
    from sqlalchemy import select

    from somno_ing.db import SwallowEventRow, db_session

    detach_ms = 240 * 60_000
    with db_session() as db:
        rows = db.scalars(
            select(SwallowEventRow).where(
                SwallowEventRow.session_id == res["session_id"],
                SwallowEventRow.source == "detected",
            )
        ).all()
    after = [r for r in rows if r.t_start_ms >= detach_ms]
    assert after, "no events detected after the sEMG electrode detached"
    assert all("semg" not in r.modality_votes for r in after)
    assert res["eval"]["f1"] >= 0.70
