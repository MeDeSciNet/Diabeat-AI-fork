"""Named, independent random streams.

Determinism (SIM-6) requires that adding a feature to one layer cannot shift the
numbers drawn by another. Every layer therefore gets its own stream, addressed
by a stable integer that must never be reused or renumbered.
"""

from __future__ import annotations

import hashlib

import numpy as np

STREAM_IDS = {
    "sleep": 1,
    "arousal": 2,
    "swallow": 3,
    "resp": 4,
    "posture": 5,
    "acoustic": 10,
    "imu": 11,
    "semg": 12,
    "artifact": 20,
    "device": 30,
}


def effective_seed(seed: int, scenario: str) -> int:
    """Fold the scenario name into the seed.

    Without this, two scenarios run at the same seed draw identical values from
    the same stream position - which means identical event UUIDs, and a primary
    key collision the moment both are ingested into one database. Reproducibility
    is per (scenario, seed), so salting costs nothing.
    """
    salt = int(hashlib.sha256(scenario.encode()).hexdigest()[:8], 16)
    return (int(seed) * 1_000_003 + salt) % (2**32)


def stream(seed: int, name: str) -> np.random.Generator:
    try:
        sid = STREAM_IDS[name]
    except KeyError:  # pragma: no cover - programming error
        raise KeyError(f"unknown RNG stream {name!r}; add it to STREAM_IDS") from None
    return np.random.default_rng([seed, sid])


def chunk_stream(seed: int, name: str, seq: int) -> np.random.Generator:
    """Per-chunk stream, so chunk N is identical whether or not chunk N-1 ran."""
    return np.random.default_rng([seed, STREAM_IDS[name], seq])
