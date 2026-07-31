// GENERATED FILE - do not edit.
// Source: packages/shared-schemas/schemas/*.json
// Regenerate with `make schemas`.

export type SleepStage = "W" | "N1" | "N2" | "N3" | "REM" | "UNKNOWN";
export const SleepStageValues = ["W", "N1", "N2", "N3", "REM", "UNKNOWN"] as const;

/** I = inspiration, E = expiration. */
export type RespPhase = "I" | "E" | "UNKNOWN";
export const RespPhaseValues = ["I", "E", "UNKNOWN"] as const;

/** E-E is the dominant pattern in healthy adults; swallow followed by inspiration (*-I) is treated as the risk-associated pattern. */
export type CoordinationPattern = "E-E" | "E-I" | "I-E" | "I-I" | "UNKNOWN";
export const CoordinationPatternValues = ["E-E", "E-I", "I-E", "I-I", "UNKNOWN"] as const;

export type Posture = "supine" | "left" | "right" | "prone" | "upright" | "UNKNOWN";
export const PostureValues = ["supine", "left", "right", "prone", "upright", "UNKNOWN"] as const;

export type EventSource = "detected" | "ground_truth" | "manual_annotation";
export const EventSourceValues = ["detected", "ground_truth", "manual_annotation"] as const;

export type Modality = "acoustic" | "imu" | "semg";
export const ModalityValues = ["acoustic", "imu", "semg"] as const;

export type RiskBand = "low" | "moderate" | "elevated" | "insufficient_data";
export const RiskBandValues = ["low", "moderate", "elevated", "insufficient_data"] as const;

/** There is deliberately no 'critical'/'emergency' level. See PRD 2.1 R1 - this system is not an active patient monitor. */
export type AlertSeverity = "info" | "advisory" | "attention";
export const AlertSeverityValues = ["info", "advisory", "attention"] as const;

export type AlertStatus = "open" | "acknowledged" | "dismissed" | "superseded";
export const AlertStatusValues = ["open", "acknowledged", "dismissed", "superseded"] as const;

/** Closed dictionary of evidence-backed, non-diagnostic care actions. */
export type RecommendedAction = "ACTION_HOB30" | "ACTION_LATERAL" | "ACTION_ORAL_CARE" | "ACTION_SUCTION_ASSESS" | "ACTION_CLINICIAN_REVIEW";
export const RecommendedActionValues = ["ACTION_HOB30", "ACTION_LATERAL", "ACTION_ORAL_CARE", "ACTION_SUCTION_ASSESS", "ACTION_CLINICIAN_REVIEW"] as const;

export type DismissReason = "poor_data_quality" | "known_condition" | "false_positive" | "other";
export const DismissReasonValues = ["poor_data_quality", "known_condition", "false_positive", "other"] as const;

/** 'autonomous' is intentionally absent - PRD 2.1 R2 forbids closed-loop actuation without human confirmation. */
export type MattressMode = "manual" | "scheduled" | "advisory_confirm";
export const MattressModeValues = ["manual", "scheduled", "advisory_confirm"] as const;

export type CommandSource = "manual" | "scheduled" | "advisory" | "safety";
export const CommandSourceValues = ["manual", "scheduled", "advisory", "safety"] as const;

export type CommandType = "set_hob_angle" | "set_lateral_tilt" | "emergency_flat";
export const CommandTypeValues = ["set_hob_angle", "set_lateral_tilt", "emergency_flat"] as const;

export type CommandStatus = "pending" | "notifying" | "running" | "completed" | "rejected" | "cancelled" | "failed";
export const CommandStatusValues = ["pending", "notifying", "running", "completed", "rejected", "cancelled", "failed"] as const;

export type LateralSide = "left" | "right" | "flat";
export const LateralSideValues = ["left", "right", "flat"] as const;

export type Role = "caregiver" | "nurse" | "researcher" | "admin";
export const RoleValues = ["caregiver", "nurse", "researcher", "admin"] as const;

export interface Waveform {
  fs_hz: number;
  /** physical_value = int16_value * scale */
  scale: number;
  unit?: string;
  data_b64: string;
}

export interface ChunkChannels {
  acoustic?: Waveform;
  imu_ax?: Waveform;
  imu_ay?: Waveform;
  imu_az?: Waveform;
  imu_gx?: Waveform;
  imu_gy?: Waveform;
  imu_gz?: Waveform;
  semg?: Waveform;
}

export interface DeviceState {
  battery_pct?: number;
  electrode_ok?: boolean;
  storage_free_pct?: number;
}

/** Transport unit published by the device (or SIM) on somno/{device_id}/signal. Waveforms are base64 int16 to keep the MQTT payload compact. */
export interface SignalChunk {
  device_id: string;
  session_id: string;
  seq: number;
  t_start_ms: number;
  duration_ms: number;
  channels: ChunkChannels;
  device_state?: DeviceState;
}

export interface SleepEpoch {
  t_start_ms: number;
  stage: SleepStage;
}

export interface ArousalEvent {
  id: string;
  t_start_ms: number;
  duration_ms: number;
}

export interface PostureSegment {
  t_start_ms: number;
  t_end_ms: number;
  posture: Posture;
  hob_angle_deg?: number | null;
}

/** Sleep staging and arousal marks. In the research setting these come from the synchronised PSG; SIM emits the same structure so ING has one code path. */
export interface PsgAnnotations {
  session_id: string;
  epoch_sec?: number;
  epochs: (SleepEpoch)[];
  arousals: (ArousalEvent)[];
  postures?: (PostureSegment)[];
}

export interface ModalityVotes {
  acoustic?: number;
  imu?: number;
  semg?: number;
}

export interface SwallowEvent {
  id: string;
  session_id: string;
  /** Milliseconds relative to session start. */
  t_start_ms: number;
  t_end_ms: number;
  confidence: number;
  source: EventSource;
  modality_votes?: ModalityVotes;
  sleep_stage?: SleepStage;
  arousal_linked?: boolean;
  arousal_id?: string | null;
  resp_phase_before?: RespPhase;
  resp_phase_after?: RespPhase;
  coordination_pattern?: CoordinationPattern;
  /** Respiratory pause associated with the swallow. Typically around 1000 ms. */
  swallow_apnea_ms?: number;
  posture?: Posture;
  hob_angle_deg?: number | null;
}

export interface SessionGap {
  from_seq: number;
  to_seq: number;
  t_start_ms?: number | null;
  t_end_ms?: number | null;
}

export interface SampleRates {
  acoustic_hz?: number;
  imu_hz?: number;
  semg_hz?: number;
}

/** One overnight recording. */
export interface Session {
  id: string;
  /** Pseudonymous subject code. Never a name, ID number or date of birth. */
  subject_code: string;
  device_id: string;
  bed_id?: string | null;
  status: "recording" | "closed" | "analyzing" | "analyzed" | "failed";
  started_at: string;
  ended_at?: string | null;
  duration_ms?: number | null;
  /** Populated when the session was produced by SIM. Null for real device data. */
  scenario?: string | null;
  seed?: number | null;
  /** Missing chunk ranges detected from sequence numbers. */
  gaps?: (SessionGap)[];
  sample_rates?: SampleRates;
}

export interface RiskComponent {
  /** Min-max normalised against the configured reference range. */
  value: number;
  weight: number;
  /** Pre-normalisation measurement, kept for transparency. */
  raw?: number | null;
}

export interface RiskComponents {
  sfi_burden: RiskComponent;
  coordination_anomaly: RiskComponent;
  supine_burden: RiskComponent;
  arousal_decoupling: RiskComponent;
}

export interface DataQuality {
  signal_coverage: number;
  artifact_ratio: number;
  band?: "ok" | "insufficient_data";
}

/** Overnight signal index. NOT a diagnosis and NOT a pneumonia or aspiration risk. UI copy must call this the 'overnight swallowing signal index'. */
export interface NightlyRisk {
  session_id: string;
  /** Null when band is insufficient_data. Higher means the signal indices deviate further from the configured reference ranges. */
  score?: number | null;
  band: RiskBand;
  components: RiskComponents;
  data_quality: DataQuality;
  algorithm_version: string;
}

/** A next-morning observation prompt. Never an emergency notification - see PRD 2.1 R1. */
export interface Alert {
  id: string;
  session_id: string;
  subject_code: string;
  bed_id?: string | null;
  rule_id: string;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  body?: string;
  /** Never empty. An alert without at least one actionable item must not be produced (PRD 2.3). */
  recommended_actions: (RecommendedAction)[];
  /** sha256(subject_code, rule_id) - drives repeat suppression. */
  dedup_key: string;
  /** Consecutive nights this dedup_key has fired. */
  repeat_nights?: number;
  created_at: string;
  /** Quiet-hours aware delivery time. */
  deliver_after?: string | null;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  dismissed_by?: string | null;
  dismissed_at?: string | null;
  dismiss_reason?: DismissReason | null;
  dismiss_note?: string | null;
  /** Values that were substituted into the rendered title/body. */
  context?: Record<string, unknown>;
}

export interface TurnSchedule {
  enabled: boolean;
  /** Floor mirrors PAM-S6 (minimum 20 minutes between motions). */
  interval_min: number;
  cycle: (LateralSide)[];
  next_at?: string | null;
}

export interface MattressState {
  bed_id: string;
  hob_angle_deg: number;
  lateral_side: LateralSide;
  lateral_deg: number;
  occupied: boolean;
  mode: MattressMode;
  moving: boolean;
  /** False puts PAM into the safe state (PAM-S8): hold position, run nothing scheduled. */
  link_ok: boolean;
  pending_command_id?: string | null;
  last_motion_at?: string | null;
  schedule?: TurnSchedule;
}

export interface MattressCommand {
  id: string;
  bed_id: string;
  type: CommandType;
  source: CommandSource;
  status: CommandStatus;
  actor_id?: string | null;
  params?: Record<string, unknown>;
  reject_reason?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface AuditLogEntry {
  id: number;
  at: string;
  actor_id: string;
  bed_id?: string | null;
  action: string;
  detail: Record<string, unknown>;
  prev_hash?: string | null;
  /** sha256 over (prev_hash, at, actor_id, action, detail) - makes the log tamper-evident (PAM-S7). */
  hash?: string;
}

export interface OnsetError {
  mean?: number;
  sd?: number;
  p50?: number;
  p90?: number;
  max?: number;
}

export interface StageBreakdown {
  n_ground_truth?: number;
  recall?: number;
}

/** Detection performance of the detected events against SIM ground truth. Development instrument only. */
export interface EvalReport {
  session_id: string;
  scenario?: string | null;
  detector_version?: string;
  tolerance_ms: number;
  n_ground_truth: number;
  n_detected: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1: number;
  onset_error_ms?: OnsetError;
  by_sleep_stage?: Record<string, StageBreakdown>;
  /** Share of true positives whose coordination_pattern matches ground truth. */
  coordination_accuracy?: number | null;
}
