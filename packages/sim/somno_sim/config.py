"""Scenario configuration for SIM.

Every number a scenario can influence lives here with a documented default. The
defaults are the literature values from the PRD appendix; scenario YAML files
override what they need.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

STAGES = ("N1", "N2", "N3", "REM")
POSTURES = ("supine", "left", "right", "prone")


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MeanSd(Base):
    mean: float
    sd: float


class SleepConfig(Base):
    # Ratios are of total recording time; W (wake) takes whatever is left over.
    stage_ratios: dict[str, float] = Field(
        default_factory=lambda: {"N1": 0.05, "N2": 0.50, "N3": 0.20, "REM": 0.25}
    )
    arousal_index: float = Field(default=15.0, description="Arousals per hour.")
    cycle_min: float = Field(default=90.0, description="NREM-REM cycle length.")
    arousal_duration_ms: MeanSd = Field(default_factory=lambda: MeanSd(mean=8000, sd=4000))
    sleep_onset_min: float = Field(default=10.0, description="Leading wake epochs.")

    @model_validator(mode="after")
    def _check(self):
        unknown = set(self.stage_ratios) - set(STAGES)
        if unknown:
            raise ValueError(f"unknown sleep stages: {sorted(unknown)}")
        total = sum(self.stage_ratios.values())
        if total > 1.0 + 1e-9:
            raise ValueError(f"stage_ratios sum to {total:.3f}, must be <= 1.0")
        return self


class SwallowConfig(Base):
    # Lichter & Muir series, via PRD appendix A. Swallows per hour of that stage.
    rates_per_hour: dict[str, float] = Field(
        default_factory=lambda: {"N1": 7.2, "N2": 2.0, "N3": 0.2, "REM": 2.7}
    )
    rate_sd_per_hour: dict[str, float] = Field(
        default_factory=lambda: {"N1": 3.5, "N2": 0.7, "N3": 0.1, "REM": 2.2},
        description="Between-subject spread. Drawn once per night, not per epoch.",
    )
    rate_scale: float = Field(
        default=1.0,
        description=(
            "Global multiplier on rates_per_hour. Exists because the PRD's per-stage "
            "rates and its whole-night count target for healthy_adult do not agree - "
            "see docs/open-questions.md OQ-1. Keeps the literature rate *shape* while "
            "letting a scenario hit a target total."
        ),
    )
    arousal_coupling_ratio: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Share of swallows anchored inside an arousal window (Burke 2020: 0.43-0.98).",
    )
    arousal_window_ms: int = Field(
        default=10000, description="Coupled swallows land within +/- this of arousal onset."
    )
    coordination_distribution: dict[str, float] = Field(
        default_factory=lambda: {"E-E": 0.85, "E-I": 0.07, "I-E": 0.05, "I-I": 0.03}
    )
    apnea_ms: MeanSd = Field(default_factory=lambda: MeanSd(mean=1000, sd=200))
    duration_ms: MeanSd = Field(
        default_factory=lambda: MeanSd(mean=900, sd=150),
        description="Duration of the acoustically/EMG observable swallow itself.",
    )
    min_interval_ms: int = 3000

    @model_validator(mode="after")
    def _check(self):
        if set(self.coordination_distribution) - {"E-E", "E-I", "I-E", "I-I"}:
            raise ValueError("coordination_distribution keys must be E-E/E-I/I-E/I-I")
        if abs(sum(self.coordination_distribution.values()) - 1.0) > 1e-6:
            raise ValueError("coordination_distribution must sum to 1.0")
        return self


class RespConfig(Base):
    rate_per_min: float = 14.0
    rate_sd_per_min: float = 1.5


class PostureConfig(Base):
    ratios: dict[str, float] = Field(
        default_factory=lambda: {"supine": 0.40, "left": 0.28, "right": 0.28, "prone": 0.04}
    )
    turns_per_hour: float = 2.0
    hob_angle_deg: float = 0.0
    transition_ms: int = 4000

    @model_validator(mode="after")
    def _check(self):
        if set(self.ratios) - set(POSTURES):
            raise ValueError(f"posture ratios must be a subset of {POSTURES}")
        if abs(sum(self.ratios.values()) - 1.0) > 1e-6:
            raise ValueError("posture ratios must sum to 1.0")
        return self


class Toggle(Base):
    enabled: bool = False
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)


class DetachConfig(Toggle):
    at_min: float = Field(default=240.0, description="Minutes into the recording.")


class ArtifactConfig(Base):
    snoring: Toggle = Field(default_factory=Toggle)
    speech: Toggle = Field(default_factory=Toggle)
    body_movement: Toggle = Field(default_factory=lambda: Toggle(enabled=True, intensity=0.4))
    cardiac: Toggle = Field(default_factory=lambda: Toggle(enabled=True, intensity=0.2))
    electrode_detach: DetachConfig = Field(default_factory=DetachConfig)
    sweat_drift: Toggle = Field(default_factory=Toggle)


class SignalConfig(Base):
    acoustic_fs_hz: int = 16000
    imu_fs_hz: int = 100
    semg_fs_hz: int = 2000
    chunk_ms: int = 5000

    # Baseline noise levels, in the physical unit of each channel.
    acoustic_noise: float = Field(default=0.004, description="Normalised sound pressure, rms.")
    imu_noise_g: float = 0.004
    semg_noise_uv: float = 5.0

    # Event amplitudes.
    swallow_acoustic_amp: float = 0.09
    swallow_imu_amp_g: float = 0.055
    swallow_semg_amp_uv: float = 70.0
    breath_acoustic_amp: float = 0.006
    resp_imu_amp_g: float = 0.018

    @model_validator(mode="after")
    def _check(self):
        if self.chunk_ms % 1000:
            raise ValueError("chunk_ms must be a whole number of seconds")
        for fs in (self.acoustic_fs_hz, self.imu_fs_hz, self.semg_fs_hz):
            if (fs * self.chunk_ms) % 1000:
                raise ValueError(f"fs {fs} Hz does not divide evenly into {self.chunk_ms} ms chunks")
        return self


class Scenario(Base):
    scenario: str
    description: str = ""
    duration_min: float = 480.0
    sleep: SleepConfig = Field(default_factory=SleepConfig)
    swallow: SwallowConfig = Field(default_factory=SwallowConfig)
    resp: RespConfig = Field(default_factory=RespConfig)
    posture: PostureConfig = Field(default_factory=PostureConfig)
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)
    signal: SignalConfig = Field(default_factory=SignalConfig)

    @property
    def duration_ms(self) -> int:
        return int(round(self.duration_min * 60_000))


SCENARIO_DIR = Path(__file__).parent / "scenarios"


def available_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIO_DIR.glob("*.yaml"))


def load_scenario(name_or_path: str | Path) -> Scenario:
    """Load a scenario by bare name (from the bundled set) or by file path."""
    path = Path(name_or_path)
    if not path.suffix:
        path = SCENARIO_DIR / f"{name_or_path}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"no scenario at {path}. Available: {', '.join(available_scenarios())}"
        )
    data: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    data.setdefault("scenario", path.stem)
    return Scenario.model_validate(data)
