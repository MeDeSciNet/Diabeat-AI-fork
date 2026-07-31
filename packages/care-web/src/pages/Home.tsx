import { useCallback, useEffect, useState } from 'react';

import type { Alert, RecommendedAction } from '@somno/types';
import { api } from '@shared/lib/api';
import { dateTime, msToHm, pct } from '@shared/lib/format';
import { useApi } from '@shared/lib/useApi';
import { useI18n } from '@shared/lib/useI18n';

import { getSubjectCode } from '../lib/subject';

/**
 * C-1 "Last night".
 *
 * One status sentence and a short list of things a caregiver can actually do.
 * The 0-100 index is deliberately absent here (PRD 7.1): a family caregiver
 * reading a bare number will over-interpret it, and there is no clinical
 * meaning to interpret. The number lives in STATION and the research views.
 */
export default function Home() {
  const { t } = useI18n();
  const subject = getSubjectCode();
  const [done, setDone] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    const sessions = await api.sessions(subject);
    const latest = sessions.find((s) => s.status === 'analyzed') ?? sessions[0] ?? null;
    if (!latest) return { session: null, risk: null, alerts: [] as Alert[] };
    const [session, alerts] = await Promise.all([
      api.session(latest.id),
      api.alerts({ session_id: latest.id }),
    ]);
    return { session, risk: session.risk, alerts };
  }, [subject]);

  const { data, loading, error, reload } = useApi(load, [subject]);

  useEffect(() => {
    if (!data?.session) return;
    api
      .careActions(subject)
      .then((actions) => setDone(new Set(actions.map((a: { action: RecommendedAction }) => a.action))))
      .catch(() => setDone(new Set()));
  }, [data?.session, subject]);

  if (loading) return <p className="py-10 text-center text-slate-500">{t('common.loading')}</p>;
  if (error)
    return (
      <div className="py-10 text-center">
        <p className="text-slate-500">{t('common.error')}</p>
        <button type="button" className="btn-ghost mt-3" onClick={reload}>
          {t('common.retry')}
        </button>
      </div>
    );

  if (!data?.session)
    return (
      <div className="card text-center">
        <p className="text-lg font-medium">{t('home.noSession')}</p>
        <p className="mt-2 text-sm text-slate-500">{t('home.noSessionHint')}</p>
      </div>
    );

  const { session, risk, alerts } = data;
  const insufficient = risk?.band === 'insufficient_data' || risk == null;
  const openAlerts = alerts.filter((a) => a.status !== 'dismissed');
  const actions = dedupeActions(openAlerts);

  const statusLine = insufficient
    ? t('status.insufficient')
    : openAlerts.length === 0
      ? t('status.inRange')
      : t('status.watch', { n: openAlerts.length });

  const tone = insufficient
    ? 'border-slate-300 bg-slate-100 dark:border-slate-700 dark:bg-slate-800/60'
    : openAlerts.length === 0
      ? 'border-sky-200 bg-sky-50 dark:border-sky-900 dark:bg-sky-950/40'
      : 'border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40';

  async function markDone(action: RecommendedAction, alertId?: string) {
    await api.recordCareAction({
      subject_code: subject,
      action,
      session_id: session!.id,
      alert_id: alertId,
    });
    setDone((prev) => new Set(prev).add(action));
    if (alertId) await api.ackAlert(alertId).catch(() => undefined);
  }

  return (
    <div className="space-y-4">
      <section className={`rounded-2xl border p-5 ${tone}`}>
        <p className="text-xl font-semibold leading-snug">{statusLine}</p>
        {insufficient && (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            {t('status.insufficientHint')}
          </p>
        )}
        <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
          <div>
            <dt className="label">{t('home.duration')}</dt>
            <dd className="mt-0.5 font-medium">{msToHm(session.duration_ms)}</dd>
          </div>
          <div>
            <dt className="label">{t('home.coverage')}</dt>
            <dd className="mt-0.5 font-medium">
              {pct(risk?.data_quality?.signal_coverage as number | undefined)}
            </dd>
          </div>
          <div>
            <dt className="label">{t('home.events')}</dt>
            <dd className="mt-0.5 font-medium">{session.n_events}</dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          {t('home.recordedAt')} {dateTime(session.started_at)}
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold">{t('home.suggestions')}</h2>
        {actions.length === 0 ? (
          <p className="card text-sm text-slate-500">{t('home.noSuggestions')}</p>
        ) : (
          <ul className="space-y-3">
            {actions.map(({ action, alert }) => {
              const isDone = done.has(action);
              return (
                <li key={action} className="card">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium leading-snug">{t(`action.${action}` as never)}</p>
                      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                        {t(`actionHint.${action}` as never)}
                      </p>
                      {alert && (
                        <p className="mt-2 text-xs text-slate-400">{alert.title}</p>
                      )}
                    </div>
                    <button
                      type="button"
                      disabled={isDone}
                      onClick={() => markDone(action, alert?.id)}
                      className={isDone ? 'btn-ghost shrink-0' : 'btn-primary shrink-0'}
                    >
                      {isDone ? `✓ ${t('home.done')}` : t('home.markDone')}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

/** One card per distinct action, keeping the alert that first asked for it. */
function dedupeActions(alerts: Alert[]): { action: RecommendedAction; alert?: Alert }[] {
  const seen = new Map<RecommendedAction, Alert>();
  for (const alert of alerts) {
    for (const action of alert.recommended_actions) {
      if (!seen.has(action)) seen.set(action, alert);
    }
  }
  return [...seen.entries()].map(([action, alert]) => ({ action, alert }));
}
