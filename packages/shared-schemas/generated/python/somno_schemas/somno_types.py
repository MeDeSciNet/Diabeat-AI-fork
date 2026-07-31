# GENERATED FILE - do not edit.
# Source: packages/shared-schemas/schemas/*.json
# Regenerate with `make schemas`.

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SleepStage(str, Enum):
    W = "W"
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"
    REM = "REM"
    UNKNOWN = "UNKNOWN"


class RespPhase(str, Enum):
    """I = inspiration, E = expiration."""

    I = "I"
    E = "E"
    UNKNOWN = "UNKNOWN"


class CoordinationPattern(str, Enum):
    """E-E is the dominant pattern in healthy adults; swallow followed by inspiration (*-I) is treated as the risk-associated pattern."""

    E_E = "E-E"
    E_I = "E-I"
    I_E = "I-E"
    I_I = "I-I"
    UNKNOWN = "UNKNOWN"


class Posture(str, Enum):
    SUPINE = "supine"
    LEFT = "left"
    RIGHT = "right"
    PRONE = "prone"
    UPRIGHT = "upright"
    UNKNOWN = "UNKNOWN"


class EventSource(str, Enum):
    DETECTED = "detected"
    GROUND_TRUTH = "ground_truth"
    MANUAL_ANNOTATION = "manual_annotation"


class Modality(str, Enum):
    ACOUSTIC = "acoustic"
    IMU = "imu"
    SEMG = "semg"


class RiskBand(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    INSUFFICIENT_DATA = "insufficient_data"


class AlertSeverity(str, Enum):
    """There is deliberately no 'critical'/'emergency' level. See PRD 2.1 R1 - this system is not an active patient monitor."""

    INFO = "info"
    ADVISORY = "advisory"
    ATTENTION = "attention"


class AlertStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    SUPERSEDED = "superseded"


class RecommendedAction(str, Enum):
    """Closed dictionary of evidence-backed, non-diagnostic care actions."""

    ACTION_HOB30 = "ACTION_HOB30"
    ACTION_LATERAL = "ACTION_LATERAL"
    ACTION_ORAL_CARE = "ACTION_ORAL_CARE"
    ACTION_SUCTION_ASSESS = "ACTION_SUCTION_ASSESS"
    ACTION_CLINICIAN_REVIEW = "ACTION_CLINICIAN_REVIEW"


class DismissReason(str, Enum):
    POOR_DATA_QUALITY = "poor_data_quality"
    KNOWN_CONDITION = "known_condition"
    FALSE_POSITIVE = "false_positive"
    OTHER = "other"


class MattressMode(str, Enum):
    """'autonomous' is intentionally absent - PRD 2.1 R2 forbids closed-loop actuation without human confirmation."""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    ADVISORY_CONFIRM = "advisory_confirm"


class CommandSource(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    ADVISORY = "advisory"
    SAFETY = "safety"


class CommandType(str, Enum):
    SET_HOB_ANGLE = "set_hob_angle"
    SET_LATERAL_TILT = "set_lateral_tilt"
    EMERGENCY_FLAT = "emergency_flat"


class CommandStatus(str, Enum):
    PENDING = "pending"
    NOTIFYING = "notifying"
    RUNNING = "running"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED = "failed"


class LateralSide(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    FLAT = "flat"


class Role(str, Enum):
    CAREGIVER = "caregiver"
    NURSE = "nurse"
    RESEARCHER = "researcher"
    ADMIN = "admin"


class Waveform(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fs_hz: float
    # physical_value = int16_value * scale
    scale: float
    unit: str | None = None
    data_b64: str


class ChunkChannels(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acoustic: Waveform | None = None
    imu_ax: Waveform | None = None
    imu_ay: Waveform | None = None
    imu_az: Waveform | None = None
    imu_gx: Waveform | None = None
    imu_gy: Waveform | None = None
    imu_gz: Waveform | None = None
    semg: Waveform | None = None


class DeviceState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    battery_pct: float | None = None
    electrode_ok: bool | None = None
    storage_free_pct: float | None = None


class SignalChunk(BaseModel):
    """Transport unit published by the device (or SIM) on somno/{device_id}/signal. Waveforms are base64 int16 to keep the MQTT payload compact."""

    model_config = ConfigDict(extra="forbid")

    device_id: str
    session_id: str
    seq: int
    t_start_ms: int
    duration_ms: int
    channels: ChunkChannels
    device_state: DeviceState | None = None


class SleepEpoch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    t_start_ms: int
    stage: SleepStage


class ArousalEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    t_start_ms: int
    duration_ms: int


class PostureSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    t_start_ms: int
    t_end_ms: int
    posture: Posture
    hob_angle_deg: float | None = None


class PsgAnnotations(BaseModel):
    """Sleep staging and arousal marks. In the research setting these come from the synchronised PSG; SIM emits the same structure so ING has one code path."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    epoch_sec: int | None = None
    epochs: list[SleepEpoch]
    arousals: list[ArousalEvent]
    postures: list[PostureSegment] | None = None


class ModalityVotes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acoustic: float | None = None
    imu: float | None = None
    semg: float | None = None


class SwallowEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    # Milliseconds relative to session start.
    t_start_ms: int
    t_end_ms: int
    confidence: float
    source: EventSource
    modality_votes: ModalityVotes | None = None
    sleep_stage: SleepStage | None = None
    arousal_linked: bool | None = None
    arousal_id: str | None = None
    resp_phase_before: RespPhase | None = None
    resp_phase_after: RespPhase | None = None
    coordination_pattern: CoordinationPattern | None = None
    # Respiratory pause associated with the swallow. Typically around 1000 ms.
    swallow_apnea_ms: int | None = None
    posture: Posture | None = None
    hob_angle_deg: float | None = None


class SessionGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_seq: int
    to_seq: int
    t_start_ms: int | None = None
    t_end_ms: int | None = None


class SampleRates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acoustic_hz: float | None = None
    imu_hz: float | None = None
    semg_hz: float | None = None


class Session(BaseModel):
    """One overnight recording."""

    model_config = ConfigDict(extra="forbid")

    id: str
    # Pseudonymous subject code. Never a name, ID number or date of birth.
    subject_code: str
    device_id: str
    bed_id: str | None = None
    status: Literal["recording", "closed", "analyzing", "analyzed", "failed"]
    started_at: str
    ended_at: str | None = None
    duration_ms: int | None = None
    # Populated when the session was produced by SIM. Null for real device data.
    scenario: str | None = None
    seed: int | None = None
    # Missing chunk ranges detected from sequence numbers.
    gaps: list[SessionGap] | None = None
    sample_rates: SampleRates | None = None


class RiskComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Min-max normalised against the configured reference range.
    value: float
    weight: float
    # Pre-normalisation measurement, kept for transparency.
    raw: float | None = None


class RiskComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sfi_burden: RiskComponent
    coordination_anomaly: RiskComponent
    supine_burden: RiskComponent
    arousal_decoupling: RiskComponent


class DataQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_coverage: float
    artifact_ratio: float
    band: Literal["ok", "insufficient_data"] | None = None


class NightlyRisk(BaseModel):
    """Overnight signal index. NOT a diagnosis and NOT a pneumonia or aspiration risk. UI copy must call this the 'overnight swallowing signal index'."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    # Null when band is insufficient_data. Higher means the signal indices deviate further from the configured reference ranges.
    score: float | None = None
    band: RiskBand
    components: RiskComponents
    data_quality: DataQuality
    algorithm_version: str


class Alert(BaseModel):
    """A next-morning observation prompt. Never an emergency notification - see PRD 2.1 R1."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    subject_code: str
    bed_id: str | None = None
    rule_id: str
    severity: AlertSeverity
    status: AlertStatus
    title: str
    body: str | None = None
    # Never empty. An alert without at least one actionable item must not be produced (PRD 2.3).
    recommended_actions: list[RecommendedAction]
    # sha256(subject_code, rule_id) - drives repeat suppression.
    dedup_key: str
    # Consecutive nights this dedup_key has fired.
    repeat_nights: int | None = None
    created_at: str
    # Quiet-hours aware delivery time.
    deliver_after: str | None = None
    acknowledged_by: str | None = None
    acknowledged_at: str | None = None
    dismissed_by: str | None = None
    dismissed_at: str | None = None
    dismiss_reason: DismissReason | None = None
    dismiss_note: str | None = None
    # Values that were substituted into the rendered title/body.
    context: dict[str, Any] | None = None


class TurnSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    # Floor mirrors PAM-S6 (minimum 20 minutes between motions).
    interval_min: int
    cycle: list[LateralSide]
    next_at: str | None = None


class MattressState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bed_id: str
    hob_angle_deg: float
    lateral_side: LateralSide
    lateral_deg: float
    occupied: bool
    mode: MattressMode
    moving: bool
    # False puts PAM into the safe state (PAM-S8): hold position, run nothing scheduled.
    link_ok: bool
    pending_command_id: str | None = None
    last_motion_at: str | None = None
    schedule: TurnSchedule | None = None


class MattressCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    bed_id: str
    type: CommandType
    source: CommandSource
    status: CommandStatus
    actor_id: str | None = None
    params: dict[str, Any] | None = None
    reject_reason: str | None = None
    created_at: str
    completed_at: str | None = None


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    at: str
    actor_id: str
    bed_id: str | None = None
    action: str
    detail: dict[str, Any]
    prev_hash: str | None = None
    # sha256 over (prev_hash, at, actor_id, action, detail) - makes the log tamper-evident (PAM-S7).
    hash: str | None = None


class OnsetError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mean: float | None = None
    sd: float | None = None
    p50: float | None = None
    p90: float | None = None
    max: float | None = None


class StageBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_ground_truth: int | None = None
    recall: float | None = None


class EvalReport(BaseModel):
    """Detection performance of the detected events against SIM ground truth. Development instrument only."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    scenario: str | None = None
    detector_version: str | None = None
    tolerance_ms: int
    n_ground_truth: int
    n_detected: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    onset_error_ms: OnsetError | None = None
    by_sleep_stage: dict[str, StageBreakdown] | None = None
    # Share of true positives whose coordination_pattern matches ground truth.
    coordination_accuracy: float | None = None
