"""SIM-6: same seed and scenario must reproduce bit for bit."""

import hashlib
from pathlib import Path

from somno_sim.publisher import NullPublisher
from somno_sim.runner import run, session_id_for


def _hash_run(cfg, seed, tmp_path: Path) -> str:
    res = run(cfg, seed=seed, device_id="dev-t", publisher=NullPublisher(), out_dir=tmp_path, speed=0.0)
    return hashlib.sha256(res.ground_truth_path.read_bytes()).hexdigest()


def test_same_seed_reproduces_ground_truth(short, tmp_path):
    cfg = short(minutes=20)
    a = _hash_run(cfg, 42, tmp_path / "a")
    b = _hash_run(cfg, 42, tmp_path / "b")
    assert a == b


def test_different_seed_changes_ground_truth(short, tmp_path):
    cfg = short(minutes=20)
    assert _hash_run(cfg, 42, tmp_path / "a") != _hash_run(cfg, 43, tmp_path / "b")


def test_waveform_is_reproducible(short):
    """Chunk rendering must not depend on anything outside the seed."""
    from somno_sim.physiology import build_night
    from somno_sim.signals import Synthesizer

    cfg = short(minutes=5)
    out = []
    for _ in range(2):
        night = build_night(cfg, 7)
        synth = Synthesizer(cfg, night, 7)
        out.append([synth.render(i, i * 5000, (i + 1) * 5000)["acoustic"].tobytes() for i in range(6)])
    assert out[0] == out[1]


def test_scenarios_at_one_seed_do_not_share_event_ids(short):
    """Two scenarios at the same seed must not mint identical UUIDs.

    They did once: every stream started at the same position, so the Nth swallow
    of any scenario got the same id and the two collided on ingest.
    """
    from somno_sim.physiology import build_night

    a = build_night(short("healthy_adult", 60), 42)
    b = build_night(short("post_stroke", 60), 42)
    assert not ({s.id for s in a.swallows} & {s.id for s in b.swallows})
    assert not ({x.id for x in a.arousals} & {x.id for x in b.arousals})


def test_session_id_is_stable_and_scenario_specific():
    assert session_id_for("healthy_adult", 42, "dev-1") == session_id_for("healthy_adult", 42, "dev-1")
    assert session_id_for("healthy_adult", 42, "dev-1") != session_id_for("post_stroke", 42, "dev-1")
