import { useCallback, useState } from 'react';

import type { Alert, DismissReason } from '@somno/types';
import { api } from '@shared/lib/api';
import { dateTime } from '@shared/lib/format';
import { useApi } from '@shared/lib/useApi';
import { useI18n } from '@shared/lib/useI18n';

const TABS = ['open', 'acknowledged', 'dismissed'] as const;
const REASONS: DismissReason[] = [
  'poor_data_quality',
  'known_condition',
  'false_positive',
  'other',
];

/**
 * S-4 alert queue.
 *
 * The dismissal dialog is not a formality. PRD 8.1 makes the reason mandatory
 * because the distribution of dismissal reasons is the only direct measurement
 * of false-positive rate a research deployment gets, and the whole fatigue
 * budget in section 2.3 depends on that number being real.
 */
export default function Queue() {
  const { t } = useI18n();
  const [tab, setTab] = useState<(typeof TABS)[number]>('open');
  const [dismissing, setDismissing] = useState<Alert | null>(null);
  const [reason, setReason] = useState<DismissReason>('false_positive');
  const [note, setNote] = useState('');

  const load = useCallback(() => api.alerts({ status: tab }), [tab]);
  const { data, loading, reload } = useApi(load, [tab]);

  async function submitDismiss() {
    if (!dismissing) return;
    await api.dismissAlert(dismissing.id, reason, note || undefined);
    setDismissing(null);
    setNote('');
    reload();
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t('queue.title')}</h2>

      <div className="flex gap-2">
        {TABS.map((s) => (
          <button
            key={s}
            type="button"
            className={tab === s ? 'btn-primary py-1' : 'btn-ghost py-1'}
            onClick={() => setTab(s)}
          >
            {t(`queue.${s}` as never)}
          </button>
        ))}
      </div>

      {loading && <p className="text-slate-500">{t('common.loading')}</p>}
      {data?.length === 0 && <p className="card text-sm text-slate-500">{t('queue.empty')}</p>}

      <ul className="space-y-3">
        {(data ?? []).map((alert) => (
          <li key={alert.id} className="card">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded px-2 py-0.5 text-[11px] font-semibold ${
                      alert.severity === 'attention'
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200'
                        : alert.severity === 'advisory'
                          ? 'bg-sky-100 text-sky-800 dark:bg-sky-900/50 dark:text-sky-200'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                    }`}
                  >
                    {t(`common.severity.${alert.severity}` as never)}
                  </span>
                  <span className="font-semibold">{alert.bed_id ?? alert.subject_code}</span>
                  {(alert.repeat_nights ?? 1) > 1 && (
                    <span className="text-xs text-slate-500">
                      {t('queue.repeat', { n: alert.repeat_nights ?? 1 })}
                    </span>
                  )}
                  <span className="ml-auto text-xs text-slate-400">
                    {dateTime(alert.created_at)}
                  </span>
                </div>

                <p className="mt-2 font-medium">{alert.title}</p>
                {alert.body && (
                  <p className="mt-1 whitespace-pre-line text-sm text-slate-600 dark:text-slate-300">
                    {alert.body}
                  </p>
                )}
                <ul className="mt-2 flex flex-wrap gap-2">
                  {alert.recommended_actions.map((a) => (
                    <li
                      key={a}
                      className="rounded-md bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800"
                    >
                      {t(`action.${a}` as never)}
                    </li>
                  ))}
                </ul>

                {alert.status === 'acknowledged' && (
                  <p className="mt-2 text-xs text-slate-500">
                    {t('queue.by')} {alert.acknowledged_by} · {dateTime(alert.acknowledged_at)}
                  </p>
                )}
                {alert.status === 'dismissed' && (
                  <p className="mt-2 text-xs text-slate-500">
                    {t(`reason.${alert.dismiss_reason}` as never)} · {alert.dismissed_by}
                    {alert.dismiss_note ? ` · ${alert.dismiss_note}` : ''}
                  </p>
                )}
              </div>

              {alert.status === 'open' && (
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={async () => {
                      await api.ackAlert(alert.id);
                      reload();
                    }}
                  >
                    {t('queue.ack')}
                  </button>
                  <button type="button" className="btn-ghost" onClick={() => setDismissing(alert)}>
                    {t('queue.dismiss')}
                  </button>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>

      {dismissing && (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl dark:bg-slate-900">
            <h3 className="text-base font-semibold">{t('queue.dismiss')}</h3>
            <p className="mt-1 text-sm text-slate-500">{dismissing.title}</p>

            <label className="label mt-4 block" htmlFor="reason">
              {t('queue.dismissReason')}
            </label>
            <select
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value as DismissReason)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            >
              {REASONS.map((r) => (
                <option key={r} value={r}>
                  {t(`reason.${r}` as never)}
                </option>
              ))}
            </select>

            <label className="label mt-4 block" htmlFor="note">
              {t('queue.dismissNote')}
            </label>
            <textarea
              id="note"
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            />

            <p className="mt-2 text-xs text-slate-500">{t('queue.reasonNote')}</p>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={() => setDismissing(null)}>
                {t('queue.cancel')}
              </button>
              <button type="button" className="btn-primary" onClick={submitDismiss}>
                {t('queue.submit')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
