/**
 * Typed clients for ING and PAM.
 *
 * Response shapes come from the generated types in shared-schemas; nothing in
 * the frontends re-declares a server type by hand.
 */
import type {
  Alert,
  MattressState,
  NightlyRisk,
  RecommendedAction,
  Session,
  SwallowEvent,
} from '@somno/types';

const ING_BASE = (import.meta as any).env?.VITE_API_BASE ?? 'http://localhost:8000';
const PAM_BASE = (import.meta as any).env?.VITE_PAM_BASE ?? 'http://localhost:8100';
const TOKEN = (import.meta as any).env?.VITE_API_TOKEN ?? 'dev-token';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(base: string, path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN}`,
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json())?.detail ?? detail;
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const ing = <T>(path: string, init?: RequestInit) => request<T>(ING_BASE, path, init);
const pam = <T>(path: string, init?: RequestInit) => request<T>(PAM_BASE, path, init);

export interface BedRow {
  bed_id: string;
  ward: string | null;
  subject_code: string | null;
  has_pam: boolean;
  session_id: string | null;
  session_status: string | null;
  band: string | null;
  light: 'grey' | 'blue' | 'amber';
  score: number | null;
  signal_coverage: number | null;
  unacknowledged_alerts: number;
  device_id: string | null;
  battery_pct: number | null;
  last_seen_at: string | null;
}

export interface TimelinePoint {
  t_ms: number;
  acoustic: number;
  semg: number;
  resp: number;
  artifact: boolean;
  snoring: boolean;
  coverage: number;
}

export interface Timeline {
  session_id: string;
  duration_ms: number | null;
  epochs: { t_start_ms: number; stage: string }[];
  arousals: { id: string; t_start_ms: number; duration_ms: number }[];
  postures: { t_start_ms: number; t_end_ms: number; posture: string; hob_angle_deg: number | null }[];
  events: SwallowEvent[];
  signal: TimelinePoint[];
}

export interface TrendNight {
  session_id: string;
  started_at: string | null;
  band: string | null;
  score: number | null;
  n_events: number | null;
  sfi_max_s: number | null;
  supine_burden: number | null;
  coordination_anomaly: number | null;
}

export interface Trend {
  subject_code: string;
  nights: TrendNight[];
  care_actions: { action: RecommendedAction; performed_at: string | null; performed_by: string }[];
}

export type SessionDetail = Session & {
  n_events: number;
  risk: (NightlyRisk & { features: Record<string, unknown>; computed_at: string | null }) | null;
};

export const api = {
  meta: () => ing<{ detector_version: string; risk_version: string; notice: string; role: string }>('/v1/meta'),

  sessions: (subjectCode?: string) =>
    ing<Session[]>(`/v1/sessions${subjectCode ? `?subject_code=${encodeURIComponent(subjectCode)}` : ''}`),
  session: (id: string) => ing<SessionDetail>(`/v1/sessions/${id}`),
  timeline: (id: string, points = 900) => ing<Timeline>(`/v1/sessions/${id}/timeline?points=${points}`),
  events: (id: string, params: Record<string, string | number> = {}) =>
    ing<{ total: number; items: SwallowEvent[] }>(
      `/v1/sessions/${id}/events?${new URLSearchParams(params as Record<string, string>)}`,
    ),
  risk: (id: string) => ing<NightlyRisk & { features: Record<string, number> }>(`/v1/sessions/${id}/risk`),
  signalWindow: (id: string, t0: number, t1: number) =>
    ing<{
      fs_hz: number;
      t_start_ms: number;
      acoustic_env: number[];
      semg_env: number[];
      imu_si: number[];
      resp_volume: number[];
      gated: number[];
    }>(`/v1/sessions/${id}/signal?t_start_ms=${t0}&t_end_ms=${t1}`),
  trend: (subjectCode: string, nights = 30) =>
    ing<Trend>(`/v1/subjects/${encodeURIComponent(subjectCode)}/trend?nights=${nights}`),

  beds: () => ing<BedRow[]>('/v1/beds'),
  shiftSummary: (shift: string) =>
    ing<{ shift: string; window: string; generated_at: string; beds: any[] }>(
      `/v1/shift-summary?shift=${shift}`,
    ),
  systemHealth: () => ing<{ devices: any[]; sessions_last_7d: number; sessions_failed: number; data_gaps: number }>(
    '/v1/system-health',
  ),

  alerts: (params: Record<string, string> = {}) =>
    ing<Alert[]>(`/v1/alerts?${new URLSearchParams(params)}`),
  ackAlert: (id: string) => ing<Alert>(`/v1/alerts/${id}/ack`, { method: 'POST' }),
  dismissAlert: (id: string, reason: string, note?: string) =>
    ing<Alert>(`/v1/alerts/${id}/dismiss`, {
      method: 'POST',
      body: JSON.stringify({ reason, note }),
    }),
  recordCareAction: (body: {
    subject_code: string;
    action: RecommendedAction;
    session_id?: string;
    alert_id?: string;
    note?: string;
  }) => ing<{ id: string }>('/v1/care-actions', { method: 'POST', body: JSON.stringify(body) }),
  careActions: (subjectCode: string) =>
    ing<{ id: string; action: RecommendedAction; performed_at: string }[]>(
      `/v1/care-actions?subject_code=${encodeURIComponent(subjectCode)}`,
    ),

  mattressState: (bedId: string) => pam<MattressState & { seconds_since_last_motion: number | null }>(
    `/v1/mattress/${bedId}/state`,
  ),
  mattressCommand: (bedId: string, body: { type: string; params: Record<string, unknown>; actor_id: string; source?: string }) =>
    pam<{ id: string; status: string }>(`/v1/mattress/${bedId}/command`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  mattressEmergencyFlat: (bedId: string, actorId: string) =>
    pam<{ id: string; status: string }>(
      `/v1/mattress/${bedId}/emergency-flat?actor_id=${encodeURIComponent(actorId)}`,
      { method: 'POST' },
    ),
  mattressMode: (bedId: string, mode: string, actorId: string) =>
    pam<MattressState>(`/v1/mattress/${bedId}/mode`, {
      method: 'PUT',
      body: JSON.stringify({ mode, actor_id: actorId }),
    }),
  mattressSchedule: (bedId: string, enabled: boolean, intervalMin: number, actorId: string) =>
    pam<{ enabled: boolean; interval_min: number }>(`/v1/mattress/${bedId}/schedule`, {
      method: 'PUT',
      body: JSON.stringify({ enabled, interval_min: intervalMin, actor_id: actorId }),
    }),
  advisories: (bedId: string) =>
    pam<{ id: string; action: string; params: Record<string, unknown>; reason: string; status: string }[]>(
      `/v1/mattress/${bedId}/advisories`,
    ),
  createAdvisory: (bedId: string, body: { action: string; params: Record<string, unknown>; reason: string }) =>
    pam<{ id: string }>(`/v1/mattress/${bedId}/advisories`, { method: 'POST', body: JSON.stringify(body) }),
  confirmAdvisory: (bedId: string, advisoryId: string, actorId: string) =>
    pam<{ id: string; status: string }>(
      `/v1/mattress/${bedId}/advisories/${advisoryId}/confirm?actor_id=${encodeURIComponent(actorId)}`,
      { method: 'POST' },
    ),
  declineAdvisory: (bedId: string, advisoryId: string, actorId: string) =>
    pam<{ declined: boolean }>(
      `/v1/mattress/${bedId}/advisories/${advisoryId}/decline?actor_id=${encodeURIComponent(actorId)}`,
      { method: 'POST' },
    ),
  mattressAudit: (bedId: string) =>
    pam<{ intact: boolean; entries: any[] }>(`/v1/mattress/${bedId}/audit`),
};
