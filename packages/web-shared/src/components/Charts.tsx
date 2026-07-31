import { useMemo, useState } from 'react';

import type { SwallowEvent } from '@somno/types';

import type { Timeline, TimelinePoint } from '../lib/api';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { POSTURE_COLOR, STAGE_COLOR, msToClock } from '../lib/format';
import { useI18n } from '../lib/useI18n';

/**
 * A band of coloured segments across the night: sleep stages, or posture.
 * Drawn as plain divs rather than a chart, because it is a categorical ribbon
 * and Recharts would make it heavier for no benefit.
 */
export function Ribbon({
  segments,
  total,
  colors,
  label,
  onSelect,
}: {
  segments: { start: number; end: number; key: string }[];
  total: number;
  colors: Record<string, string>;
  label: string;
  onSelect?: (t: number) => void;
}) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium text-slate-500 dark:text-slate-400">{label}</div>
      <div className="flex h-5 w-full overflow-hidden rounded" role="img" aria-label={label}>
        {segments.map((seg, i) => (
          <button
            key={i}
            type="button"
            title={`${seg.key} · ${msToClock(seg.start)}`}
            onClick={() => onSelect?.(seg.start)}
            className="h-full border-0 p-0"
            style={{
              width: `${Math.max(0, ((seg.end - seg.start) / Math.max(total, 1)) * 100)}%`,
              background: colors[seg.key] ?? colors.UNKNOWN,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export function stageSegments(timeline: Timeline) {
  const out: { start: number; end: number; key: string }[] = [];
  const epochs = timeline.epochs;
  for (let i = 0; i < epochs.length; i += 1) {
    const end = i + 1 < epochs.length ? epochs[i + 1].t_start_ms : (timeline.duration_ms ?? epochs[i].t_start_ms + 30000);
    if (out.length && out[out.length - 1].key === epochs[i].stage) out[out.length - 1].end = end;
    else out.push({ start: epochs[i].t_start_ms, end, key: epochs[i].stage });
  }
  return out;
}

export function postureSegments(timeline: Timeline) {
  return timeline.postures.map((p) => ({ start: p.t_start_ms, end: p.t_end_ms, key: p.posture }));
}

/** Whole-night signal chart with drag-to-zoom and event markers. */
export function NightChart({
  timeline,
  onSelectEvent,
}: {
  timeline: Timeline;
  onSelectEvent?: (eventId: string) => void;
}) {
  const { t } = useI18n();
  const [range, setRange] = useState<[number, number] | null>(null);
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  const [dragTo, setDragTo] = useState<number | null>(null);

  const total = timeline.duration_ms ?? timeline.signal.at(-1)?.t_ms ?? 1;
  const [lo, hi] = range ?? [0, total];

  const data = useMemo(
    () => timeline.signal.filter((p) => p.t_ms >= lo && p.t_ms <= hi),
    [timeline.signal, lo, hi],
  );
  const events = useMemo(
    () => timeline.events.filter((e) => e.t_start_ms >= lo && e.t_start_ms <= hi),
    [timeline.events, lo, hi],
  );
  const artifactSpans = useMemo(() => spansOf(data, (p: TimelinePoint) => p.artifact), [data]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{t('timeline.zoomHint')}</span>
        {range && (
          <button
            type="button"
            className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800"
            onClick={() => setRange(null)}
          >
            {t('timeline.reset')}
          </button>
        )}
      </div>

      <Ribbon
        label={t('timeline.stages')}
        segments={stageSegments(timeline).filter((s) => s.end >= lo && s.start <= hi)}
        total={hi - lo}
        colors={STAGE_COLOR}
      />
      <Ribbon
        label={t('timeline.posture')}
        segments={postureSegments(timeline).filter((s) => s.end >= lo && s.start <= hi)}
        total={hi - lo}
        colors={POSTURE_COLOR}
      />

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            onMouseDown={(e: any) => e?.activeLabel != null && setDragFrom(Number(e.activeLabel))}
            onMouseMove={(e: any) => dragFrom != null && e?.activeLabel != null && setDragTo(Number(e.activeLabel))}
            onMouseUp={() => {
              if (dragFrom != null && dragTo != null && Math.abs(dragTo - dragFrom) > 10_000) {
                setRange([Math.min(dragFrom, dragTo), Math.max(dragFrom, dragTo)]);
              }
              setDragFrom(null);
              setDragTo(null);
            }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
            <XAxis
              dataKey="t_ms"
              type="number"
              domain={[lo, hi]}
              tickFormatter={(v) => msToClock(Number(v)).slice(0, 5)}
              fontSize={11}
            />
            <YAxis fontSize={11} width={40} />
            <Tooltip
              labelFormatter={(v: number) => msToClock(Number(v))}
              formatter={(value: unknown, name: unknown) => [Number(value).toPrecision(3), String(name)]}
            />
            {artifactSpans.map(([a, b]: [number, number], i: number) => (
              <ReferenceArea key={i} x1={a} x2={b} fill="#94a3b8" fillOpacity={0.25} />
            ))}
            <Area
              type="monotone"
              dataKey="acoustic"
              name={t('timeline.signal')}
              stroke="#0ea5e9"
              fill="#bae6fd"
              isAnimationActive={false}
            />
            {dragFrom != null && dragTo != null && (
              <ReferenceArea x1={dragFrom} x2={dragTo} fillOpacity={0.15} />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div>
        <div className="mb-1 text-xs font-medium text-slate-500 dark:text-slate-400">
          {t('timeline.events')} ({events.length})
        </div>
        <div className="relative h-8 w-full rounded bg-slate-100 dark:bg-slate-800">
          {events.map((e: SwallowEvent) => (
            <button
              key={e.id}
              type="button"
              onClick={() => onSelectEvent?.(e.id)}
              title={`${msToClock(e.t_start_ms)} · ${e.coordination_pattern}`}
              className="absolute top-1 h-6 w-1.5 -translate-x-1/2 rounded-sm hover:h-7 hover:w-2"
              style={{
                left: `${((e.t_start_ms - lo) / Math.max(hi - lo, 1)) * 100}%`,
                background: e.coordination_pattern?.endsWith('-I') ? '#f97316' : '#0ea5e9',
                opacity: 0.35 + 0.65 * (e.confidence ?? 0.5),
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function spansOf(rows: TimelinePoint[], pred: (row: TimelinePoint) => boolean): [number, number][] {
  const out: [number, number][] = [];
  let start: number | null = null;
  rows.forEach((row, i) => {
    if (pred(row) && start === null) start = row.t_ms;
    if (!pred(row) && start !== null) {
      out.push([start, row.t_ms]);
      start = null;
    }
    if (i === rows.length - 1 && start !== null) out.push([start, row.t_ms]);
  });
  return out;
}

/** Radar of the four index components. Station and research views only. */
export function ComponentRadar({ components }: { components: Record<string, { value: number }> }) {
  const data = Object.entries(components).map(([name, c]) => ({
    component: name.replace(/_/g, ' '),
    value: Number((c.value * 100).toFixed(1)),
  }));
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="70%">
          <PolarGrid className="stroke-slate-300 dark:stroke-slate-600" />
          <PolarAngleAxis dataKey="component" fontSize={11} />
          <PolarRadiusAxis domain={[0, 100]} fontSize={10} />
          <Radar dataKey="value" stroke="#0284c7" fill="#38bdf8" fillOpacity={0.45} />
          <Tooltip />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TrendLine({
  data,
  dataKey,
  label,
  color = '#0ea5e9',
}: {
  data: Record<string, unknown>[];
  dataKey: string;
  label: string;
  color?: string;
}) {
  return (
    <div className="h-44 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
          <XAxis dataKey="date" fontSize={11} />
          <YAxis fontSize={11} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey={dataKey}
            name={label}
            stroke={color}
            strokeWidth={2}
            dot={{ r: 3 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
