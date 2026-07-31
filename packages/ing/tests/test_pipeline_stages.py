"""Stage-level tests for gating, ingest bookkeeping and the transport codec."""

from __future__ import annotations

import numpy as np
import pytest

from somno_ing.detect import DERIVED_FS, Derived
from somno_ing.detect import gating
from somno_ing.detect.preprocess import Preprocessor, finalize_resp, wavelet_denoise
from somno_ing.ingest import SessionIngestor, decode_channels, summary_rows


def _blank(seconds: int) -> Derived:
    n = int(seconds * DERIVED_FS)
    d = Derived()
    for name in Derived.ARRAYS:
        setattr(d, name, np.zeros(n, dtype=np.float32))
    d.present = np.ones(n, bool)
    d.semg_ok = np.ones(n, bool)
    return d


# ------------------------------------------------------------------ gating
def test_sustained_motion_is_gated():
    d = _blank(120)
    a, b = int(30 * DERIVED_FS), int(34 * DERIVED_FS)
    d.imu_dyn[a:b] = 0.4
    result = gating.apply(d)
    assert d.gated[a + 100 : b - 100].all()
    assert 0.0 < result.movement_ratio < 0.3


def test_a_swallows_own_excursion_is_not_gated_as_movement():
    """The regression that mattered: peak-based gating deleted true events."""
    d = _blank(120)
    for centre in (20, 45, 70, 95):
        a = int(centre * DERIVED_FS)
        b = a + int(0.9 * DERIVED_FS)
        d.imu_dyn[a:b] = 0.055  # hyoid excursion, same order as a gentle turn
    gating.apply(d)
    assert not d.gated.any(), "a swallow was gated as body movement"


def test_snoring_is_flagged_but_not_gated():
    d = _blank(300)
    a, b = int(60 * DERIVED_FS), int(240 * DERIVED_FS)
    d.snore_env[a:b] = 0.05
    d.acoustic_env[:] = 0.004
    result = gating.apply(d)
    assert d.snoring[a + 500 : b - 500].any(), "snoring was not flagged"
    assert not d.gated[a:b].any(), "snoring was hard-gated"
    assert result.artifact_ratio == 0.0, "snoring counted towards artifact_ratio"


def test_absent_samples_are_gated_and_reduce_coverage():
    d = _blank(120)
    a, b = int(20 * DERIVED_FS), int(50 * DERIVED_FS)
    d.present[a:b] = False
    result = gating.apply(d)
    assert d.gated[a:b].all()
    assert result.artifact_ratio == pytest.approx(0.25, abs=0.01)


# ------------------------------------------------------------- preprocess
def test_respiration_filter_is_zero_phase():
    """A causal filter here costs ~0.95 s of delay - a quarter of a breath."""
    d = _blank(300)
    t = np.arange(len(d)) / DERIVED_FS
    d.resp_volume = (0.5 * np.sin(2 * np.pi * 0.233 * t) - 0.9).astype(np.float32)
    finalize_resp(d)

    reference = np.sin(2 * np.pi * 0.233 * t)
    a, b = int(30 * DERIVED_FS), int(270 * DERIVED_FS)
    x = d.resp_volume[a:b].astype(np.float64)
    y = reference[a:b]
    corr = float(np.corrcoef(x, y)[0, 1])
    assert corr > 0.99, f"phase was shifted (correlation {corr:.3f})"
    assert abs(float(np.mean(x))) < 0.01, "the DC offset survived the band-pass"


def test_wavelet_denoise_preserves_a_burst_and_lowers_the_floor():
    rng = np.random.default_rng(0)
    n = 4096
    x = rng.normal(0, 0.01, n).astype(np.float32)
    x[2000:2060] += 0.5
    out = wavelet_denoise(x)
    assert out[2000:2060].max() > 0.3, "the burst was flattened"
    assert np.std(out[:1500]) < np.std(x[:1500])


def test_preprocessor_reduces_a_chunk_to_the_derived_rate():
    fs = {"acoustic": 16000.0, "semg": 2000.0, **{f"imu_{a}": 100.0 for a in ("ax", "ay", "az", "gx", "gy", "gz")}}
    pre = Preprocessor(fs)
    seconds = 5
    channels = {
        "acoustic": np.random.default_rng(1).normal(0, 0.01, int(16000 * seconds)),
        "semg": np.random.default_rng(2).normal(0, 5.0, int(2000 * seconds)),
        **{f"imu_{a}": np.zeros(int(100 * seconds)) for a in ("ax", "ay", "az", "gx", "gy", "gz")},
    }
    channels["imu_ax"][:] = -1.0
    out = pre.process(channels)
    assert len(out) == int(DERIVED_FS * seconds)
    assert out.acoustic_env.dtype == np.float32
    assert np.isfinite(out.acoustic_env).all()


# ---------------------------------------------------------------- ingest
def _chunk(seq: int, t_start_ms: int, duration_ms: int = 5000) -> dict:
    from somno_sim.publisher import encode_chunk
    from somno_sim.signals import CHANNELS

    fs = {"acoustic": 16000.0, "semg": 2000.0, **{f"imu_{a}": 100.0 for a in ("ax", "ay", "az", "gx", "gy", "gz")}}
    rng = np.random.default_rng(seq)
    channels = {}
    for name in CHANNELS:
        n = int(fs[name] * duration_ms / 1000)
        channels[name] = rng.normal(0, 0.01, n)
    return encode_chunk("dev-t", "sess-t", seq, t_start_ms, duration_ms, channels, fs)


def test_chunks_round_trip_through_the_wire_format():
    payload = _chunk(0, 0)
    channels, fs = decode_channels(payload)
    assert fs["acoustic"] == 16000.0
    assert len(channels["acoustic"]) == 80_000
    assert np.abs(channels["acoustic"]).max() < 1.0


def test_a_dropped_run_of_chunks_is_recorded_as_one_gap():
    ing = SessionIngestor(session_id="sess-t", device_id="dev-t", duration_ms=50_000)
    for seq in range(10):
        if 3 <= seq < 7:
            continue
        ing.on_chunk(_chunk(seq, seq * 5000))
    assert len(ing.gaps) == 1
    assert ing.gaps[0]["from_seq"] == 3 and ing.gaps[0]["to_seq"] == 6
    assert ing.signal_coverage == pytest.approx(0.6, abs=0.01)


def test_duplicate_redelivery_is_ignored():
    """MQTT QoS 1 is at-least-once, so the same chunk can arrive twice."""
    ing = SessionIngestor(session_id="sess-t", device_id="dev-t", duration_ms=10_000)
    ing.on_chunk(_chunk(0, 0))
    ing.on_chunk(_chunk(1, 5000))
    ing.on_chunk(_chunk(1, 5000))
    assert ing.chunks_received == 2
    assert len(ing.derived) == int(DERIVED_FS * 10)


def test_summary_rows_are_one_per_second():
    d = _blank(120)
    rows = summary_rows("sess-t", d)
    assert len(rows) == 120
    assert rows[1]["t_ms"] == 1000
    assert set(rows[0]) >= {"acoustic_rms", "semg_rms", "posture", "artifact", "coverage"}
