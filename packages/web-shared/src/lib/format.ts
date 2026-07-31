/** Formatting helpers shared by both apps. */

export function msToClock(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function msToHm(ms: number | null | undefined): string {
  if (ms == null) return '-';
  const minutes = Math.round(ms / 60000);
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function pct(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return '-';
  return `${(value * 100).toFixed(digits)}%`;
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return '-';
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString();
}

export const STAGE_COLOR: Record<string, string> = {
  W: '#cbd5e1',
  N1: '#93c5fd',
  N2: '#60a5fa',
  N3: '#2563eb',
  REM: '#a78bfa',
  UNKNOWN: '#e2e8f0',
};

export const POSTURE_COLOR: Record<string, string> = {
  supine: '#f59e0b',
  left: '#34d399',
  right: '#22d3ee',
  prone: '#fb7185',
  upright: '#a3e635',
  UNKNOWN: '#e2e8f0',
};

/** Three states only. Red would imply urgency, which PRD 2.1 R1 rules out. */
export const LIGHT_CLASS: Record<string, string> = {
  grey: 'bg-slate-300 dark:bg-slate-600',
  blue: 'bg-sky-500',
  amber: 'bg-amber-500',
};
