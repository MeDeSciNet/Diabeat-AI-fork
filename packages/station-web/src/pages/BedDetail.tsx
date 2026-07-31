import { useCallback, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { ComponentRadar, NightChart } from '@shared/components/Charts';
import { api } from '@shared/lib/api';
import { msToClock, msToHm, pct } from '@shared/lib/format';
import { useApi } from '@shared/lib/useApi';
import { useI18n } from '@shared/lib/useI18n';

const PATTERNS = ['E-E', 'E-I', 'I-E', 'I-I', 'UNKNOWN'];

/**
 * S-3 bed detail. The one place the 0-100 index and its components are shown,
 * with the wording that keeps it a signal index rather than a clinical finding.
 */
export default function BedDetail() {
  const { t } = useI18n();
  const { bedId = '' } = useParams();
  const [minConfidence, setMinConfidence] = useState(0);
  const [pattern, setPattern] = useState('');
  const [windowStart, setWindowStart] = useState(0);

  const load = useCallback(async () => {
    const beds = await api.beds();
    const bed = beds.find((b) => b.bed_id === bedId);
    if (!bed?.session_id) return null;
    const [session, timeline] = await Promise.all([
      api.session(bed.session_id),
      api.timeline(bed.session_id, 1200),
    ]);
    return { bed, session, timeline };
  }, [bedId]);

  const { data, loading } = useApi(load, [bedId]);

  const eventsQuery = useCallback(async () => {
    if (!data?.session) return null;
    return api.events(data.session.id, {
      limit: 500,
      min_confidence: minConfidence,
      ...(pattern ? { coordination_pattern: pattern } : {}),
    });
  }, [data?.session, minConfidence, pattern]);
  const { data: events } = useApi(eventsQuery, [data?.session?.id, minConfidence, pattern]);

  const signalQuery = useCallback(async () => {
    if (!data?.session) return null;
    return api.signalWindow(data.session.id, windowStart, windowStart + 60_000);
  }, [data?.session, windowStart]);
  const { data: signal } = useApi(signalQuery, [data?.session?.id, windowStart]);

  if (loading) return <p className="py-10 text-center text-slate-500">{t('common.loading')}</p>;
  if (!data)
    return (
      <div className="py-10 text-center">
        <p className="text-slate-500">{t('beds.noSession')}</p>
        <Link to="/beds" className="btn-ghost mt-4 inline-flex">
          {t('common.back')}
        </Link>
      </div>
    );

  const { bed, session, timeline } = data;
  const risk = session.risk;
  const features = (risk?.features ?? {}) as Record<string, number>;

  const signalRows =
    signal?.acoustic_env.map((v, i) => ({
      t: Math.round(signal.t_start_ms + (i * 1000) / signal.fs_hz),
      acoustic: v,
      semg: signal.semg_env[i],
      imu: signal.imu_si[i],
      resp: signal.resp_volume[i],
    })) ?? [];

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-4">
        <Link to="/beds" className="btn-ghost py-1">
          ← {t('common.back')}
        </Link>
        <h2 className="text-xl font-semibold">
          {bed.bed_id} · {bed.subject_code}
        </h2>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <section className="card lg:col-span-2">
          <h3 className="mb-3 text-sm font-semibold">{t('timeline.title')}</h3>
          <NightChart timeline={timeline} />
        </section>

        <section className="card">
          <h3 className="text-sm font-semibold">{t('index.name')}</h3>
          {risk?.band === 'insufficient_data' || risk?.score == null ? (
            <p className="mt-3 text-sm text-slate-500">{t('status.insufficient')}</p>
          ) : (
            <>
              <p className="mt-2 text-5xl font-bold tabular-nums">{risk.score.toFixed(0)}</p>
              <p className="mt-1 text-sm text-slate-500">{t(`band.${risk.band}` as never)}</p>
            </>
          )}
          <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            {t('index.explain')}
          </p>

          <h4 className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('detail.components')}
          </h4>
          {risk?.components && <ComponentRadar components={risk.components as never} />}

          <dl className="mt-2 space-y-1 text-xs">
            <Row label={t('home.duration')} value={msToHm(session.duration_ms)} />
            <Row label={t('home.coverage')} value={pct(risk?.data_quality?.signal_coverage as number)} />
            <Row label="artifact" value={pct(risk?.data_quality?.artifact_ratio as number)} />
            <Row label={t('home.events')} value={String(session.n_events)} />
            <Row label="algorithm" value={risk?.algorithm_version ?? '-'} />
          </dl>
        </section>
      </div>

      <section className="card">
        <div className="mb-3 flex flex-wrap items-end gap-4">
          <h3 className="text-sm font-semibold">{t('detail.events')}</h3>
          <label className="text-xs">
            <span className="label block">{t('detail.filterConfidence')}</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="mt-1 accent-sky-600"
            />
            <span className="ml-2 tabular-nums">{minConfidence.toFixed(2)}</span>
          </label>
          <label className="text-xs">
            <span className="label block">{t('detail.filterPattern')}</span>
            <select
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              className="mt-1 rounded border border-slate-300 bg-white px-2 py-1 dark:border-slate-600 dark:bg-slate-900"
            >
              <option value="">{t('detail.all')}</option>
              {PATTERNS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <span className="ml-auto text-xs text-slate-500">{events?.total ?? 0}</span>
        </div>

        <div className="max-h-96 overflow-auto">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-slate-50 text-slate-500 dark:bg-slate-800">
              <tr>
                <th className="px-2 py-1.5">{t('event.time')}</th>
                <th className="px-2 py-1.5">{t('event.confidence')}</th>
                <th className="px-2 py-1.5">{t('event.pattern')}</th>
                <th className="px-2 py-1.5">{t('event.stage')}</th>
                <th className="px-2 py-1.5">{t('event.posture')}</th>
                <th className="px-2 py-1.5">{t('event.apnea')}</th>
                <th className="px-2 py-1.5">{t('event.votes')}</th>
              </tr>
            </thead>
            <tbody>
              {(events?.items ?? []).map((e) => (
                <tr
                  key={e.id}
                  className="cursor-pointer border-t border-slate-100 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/60"
                  onClick={() => setWindowStart(Math.max(0, e.t_start_ms - 20_000))}
                >
                  <td className="px-2 py-1 font-mono">{msToClock(e.t_start_ms)}</td>
                  <td className="px-2 py-1 tabular-nums">{e.confidence.toFixed(2)}</td>
                  <td className="px-2 py-1">{e.coordination_pattern}</td>
                  <td className="px-2 py-1">{e.sleep_stage}</td>
                  <td className="px-2 py-1">{e.posture}</td>
                  <td className="px-2 py-1 tabular-nums">{e.swallow_apnea_ms ?? '-'}</td>
                  <td className="px-2 py-1 font-mono text-[10px]">
                    {Object.entries(e.modality_votes ?? {})
                      .map(([k, v]) => `${k[0]}${Number(v).toFixed(2)}`)
                      .join(' ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h3 className="text-sm font-semibold">{t('detail.viewer')}</h3>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t('detail.viewerHint')}</p>
        <div className="mt-3 flex items-center gap-3 text-xs">
          <span className="label">{t('detail.window')}</span>
          <input
            type="range"
            min={0}
            max={Math.max(0, (session.duration_ms ?? 60_000) - 60_000)}
            step={30_000}
            value={windowStart}
            onChange={(e) => setWindowStart(Number(e.target.value))}
            className="w-72 accent-sky-600"
          />
          <span className="font-mono">{msToClock(windowStart)}</span>
        </div>
        <div className="mt-2 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={signalRows} margin={{ left: -10, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
              <XAxis dataKey="t" tickFormatter={(v) => msToClock(Number(v))} fontSize={10} />
              <YAxis fontSize={10} />
              <Tooltip labelFormatter={(v) => msToClock(Number(v))} />
              <Line type="monotone" dataKey="acoustic" stroke="#0ea5e9" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="semg" stroke="#f97316" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="imu" stroke="#10b981" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="resp" stroke="#a855f7" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="card">
        <h3 className="mb-2 text-sm font-semibold">features</h3>
        <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs md:grid-cols-4">
          {Object.entries(features)
            .filter(([, v]) => typeof v === 'number')
            .map(([k, v]) => (
              <Row key={k} label={k} value={String(v)} />
            ))}
        </div>
      </section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}
