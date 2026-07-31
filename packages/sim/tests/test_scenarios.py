"""Every bundled scenario, plus the EDF+ round trip (PRD 5.3)."""

from __future__ import annotations

import numpy as np
import pytest

from somno_sim.config import available_scenarios, load_scenario
from somno_sim.publisher import CallbackPublisher, NullPublisher, decode_channel
from somno_sim.runner import run
from somno_sim.signals import CHANNELS


def test_five_scenarios_are_bundled():
    names = available_scenarios()
    assert set(names) == {
        "healthy_adult",
        "elderly_high_risk",
        "post_stroke",
        "noisy_signal",
        "sensor_failure",
    }


@pytest.mark.parametrize("scenario", available_scenarios())
def test_scenario_runs_without_crashing(scenario, tmp_path):
    cfg = load_scenario(scenario).model_copy(update={"duration_min": 15.0})
    result = run(cfg, seed=5, device_id="dev-t", publisher=NullPublisher(), out_dir=tmp_path, speed=0.0)
    assert result.n_chunks > 0
    assert result.ground_truth_path.exists()


def test_published_chunks_decode_to_the_declared_channels():
    cfg = load_scenario("healthy_adult").model_copy(update={"duration_min": 1.0})
    seen: list[dict] = []
    run(
        cfg,
        seed=1,
        device_id="dev-t",
        publisher=CallbackPublisher(lambda topic, payload: seen.append({"topic": topic, **payload})),
        out_dir=None,
        speed=0.0,
    )
    signal = [m for m in seen if m["topic"].endswith("/signal")]
    assert signal, "nothing was published"
    first = signal[0]
    assert set(first["channels"]) == set(CHANNELS)
    acoustic = decode_channel(first["channels"]["acoustic"])
    assert len(acoustic) == cfg.signal.acoustic_fs_hz * cfg.signal.chunk_ms // 1000
    assert np.isfinite(acoustic).all()


def test_control_messages_bracket_the_session():
    cfg = load_scenario("healthy_adult").model_copy(update={"duration_min": 1.0})
    seen: list[dict] = []
    run(
        cfg,
        seed=1,
        device_id="dev-t",
        publisher=CallbackPublisher(lambda topic, payload: seen.append({"topic": topic, **payload})),
        out_dir=None,
        speed=0.0,
    )
    control = [m for m in seen if m["topic"].endswith("/control")]
    assert [m["event"] for m in control] == ["session_start", "session_end"]
    assert control[0]["psg"]["epochs"], "PSG annotations were not published"


def test_device_state_reports_electrode_detachment():
    cfg = load_scenario("sensor_failure").model_copy(update={"duration_min": 300.0})
    states: list[tuple[int, bool]] = []
    run(
        cfg,
        seed=1,
        device_id="dev-t",
        publisher=CallbackPublisher(
            lambda topic, payload: states.append(
                (payload["t_start_ms"], payload["device_state"]["electrode_ok"])
            )
            if topic.endswith("/signal")
            else None
        ),
        out_dir=None,
        speed=0.0,
    )
    detach_ms = cfg.artifacts.electrode_detach.at_min * 60_000
    assert all(ok for t, ok in states if t < detach_ms - 10_000)
    assert not any(ok for t, ok in states if t > detach_ms + 10_000)


def test_edf_export_is_readable_by_pyedflib(tmp_path):
    """PRD 5.3: the EDF+ output must read back correctly."""
    import pyedflib

    cfg = load_scenario("healthy_adult").model_copy(update={"duration_min": 2.0})
    result = run(
        cfg,
        seed=3,
        device_id="dev-t",
        publisher=NullPublisher(),
        out_dir=tmp_path,
        speed=0.0,
        export_edf=True,
    )
    assert result.edf_path and result.edf_path.exists()

    with pyedflib.EdfReader(str(result.edf_path)) as reader:
        labels = reader.getSignalLabels()
        assert set(labels) == set(CHANNELS)
        acoustic = reader.readSignal(labels.index("acoustic"))
        expected = cfg.signal.acoustic_fs_hz * int(cfg.duration_min * 60)
        assert abs(len(acoustic) - expected) <= cfg.signal.acoustic_fs_hz
        assert np.isfinite(acoustic).all()
        annotations = reader.readAnnotations()[2]
        assert any("swallow" in a for a in annotations)
        assert any("stage" in a for a in annotations)


def test_ground_truth_carries_every_field_the_schema_requires(tmp_path):
    import json

    from somno_schemas import SwallowEvent

    cfg = load_scenario("elderly_high_risk").model_copy(update={"duration_min": 30.0})
    result = run(cfg, seed=8, device_id="dev-t", publisher=NullPublisher(), out_dir=tmp_path, speed=0.0)
    doc = json.loads(result.ground_truth_path.read_text())

    assert doc["scenario"] == "elderly_high_risk"
    assert doc["psg"]["epochs"] and doc["psg"]["postures"]
    events = [SwallowEvent.model_validate(e) for e in doc["swallow_events"]]
    assert events
    for e in events:
        assert e.source.value == "ground_truth"
        assert e.coordination_pattern.value in ("E-E", "E-I", "I-E", "I-I")
        assert e.t_end_ms > e.t_start_ms
        assert e.swallow_apnea_ms and e.swallow_apnea_ms > 0
