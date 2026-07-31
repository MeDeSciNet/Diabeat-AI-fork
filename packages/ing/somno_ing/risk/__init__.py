"""Overnight signal index (PRD 6.4).

Four normalised components, fixed weights, one number. Two things this file is
strict about:

* The output is never called a risk of anything clinical. It is a signal index,
  and ``NightlyRisk.score`` carries no diagnostic meaning.
* A night that fails the data-quality gate gets no score at all - not a low one.
  ``insufficient_data`` is a distinct state, and the alert engine refuses to
  fire on it.

Reference ranges live in ``config/risk.yaml`` because they are provisional
literature values, not settled facts. See docs/open-questions.md OQ-2.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ..features import NightFeatures
from ..settings import get_settings

RISK_VERSION = "risk-v1.0.0"

BAND_EDGES = ((33.0, "low"), (66.0, "moderate"), (100.0, "elevated"))


@dataclass
class DataQuality:
    signal_coverage: float
    artifact_ratio: float

    @property
    def band(self) -> str:
        return "ok" if self.is_ok else "insufficient_data"

    @property
    def is_ok(self) -> bool:
        return self.signal_coverage >= 0.6 and self.artifact_ratio <= 0.4

    def to_dict(self) -> dict:
        return {
            "signal_coverage": round(self.signal_coverage, 4),
            "artifact_ratio": round(self.artifact_ratio, 4),
            "band": self.band,
        }


class RiskConfig:
    def __init__(self, path: Path | None = None) -> None:
        p = Path(path or get_settings().risk_config)
        raw = yaml.safe_load(p.read_text()) if p.exists() else {}
        self.version: str = raw.get("algorithm_version", RISK_VERSION)
        self.components: dict[str, dict] = raw["components"]
        self.quality: dict[str, float] = raw.get(
            "quality", {"min_signal_coverage": 0.6, "max_artifact_ratio": 0.4}
        )
        ref = raw.get("arousal_coupling_reference", {})
        self.arousal_reference_low: float = ref.get("low", 0.43)
        self.arousal_min_events: int = int(ref.get("min_events", 10))


def _normalise(raw: float, ref: dict) -> float:
    lo, hi = float(ref["low"]), float(ref["high"])
    if hi == lo:
        return 0.0
    return float(min(1.0, max(0.0, (raw - lo) / (hi - lo))))


def raw_components(features: NightFeatures, cfg: RiskConfig) -> dict[str, float]:
    # Decoupling is measured as the shortfall below the published lower bound of
    # normal arousal-swallow coupling (Burke 2020: 0.43-0.98), scaled to 0-1.
    #
    # Too few events and the ratio is undefined rather than zero. Reporting a
    # near-empty night as maximally decoupled would be the worst kind of wrong:
    # confident, and driven entirely by missing data.
    ref_low = cfg.arousal_reference_low
    if features.n_events < cfg.arousal_min_events:
        shortfall = 0.0
    else:
        shortfall = max(0.0, ref_low - features.arousal_coupling) / max(ref_low, 1e-9)
    return {
        "sfi_burden": features.sfi_burden,
        "coordination_anomaly": features.coordination_anomaly,
        "supine_burden": features.supine_burden,
        "arousal_decoupling": shortfall,
    }


def score(
    features: NightFeatures,
    quality: DataQuality,
    cfg: RiskConfig | None = None,
) -> dict:
    cfg = cfg or RiskConfig()
    raws = raw_components(features, cfg)

    components = {}
    total = 0.0
    for name, ref in cfg.components.items():
        value = _normalise(raws[name], ref)
        weight = float(ref["weight"])
        total += value * weight
        components[name] = {
            "value": round(value, 4),
            "weight": weight,
            "raw": round(raws[name], 4),
        }

    ok = (
        quality.signal_coverage >= cfg.quality["min_signal_coverage"]
        and quality.artifact_ratio <= cfg.quality["max_artifact_ratio"]
    )
    if not ok:
        return {
            "score": None,
            "band": "insufficient_data",
            "components": components,
            "data_quality": quality.to_dict(),
            "algorithm_version": cfg.version,
        }

    value = round(100.0 * total, 1)
    band = next(name for edge, name in BAND_EDGES if value <= edge)
    return {
        "score": value,
        "band": band,
        "components": components,
        "data_quality": quality.to_dict(),
        "algorithm_version": cfg.version,
    }
