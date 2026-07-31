import { useCallback, useState } from 'react';

import { TrendLine } from '@shared/components/Charts';
import { api, type TrendNight } from '@shared/lib/api';
import { shortDate } from '@shared/lib/format';
import { useApi } from '@shared/lib/useApi';
import { useI18n } from '@shared/lib/useI18n';

import { getSubjectCode } from '../lib/subject';

/**
 * C-3 trend.
 *
 * The care-action markers are the point of this screen: seeing "the nights we
 * did oral care" against "the nights we did not" is the only feedback loop a
 * caregiver gets, and it is what makes the suggestions feel worth following.
 */
export default function Trend() {
  const { t } = useI18n();
  const subject = getSubjectCode();
  const [nights, setNights] = useState(7);

  const load = useCallback(() => api.trend(subject, nights), [subject, nights]);
  const { data, loading } = useApi(load, [subject, nights]);

  if (loading) return <p className="py-10 text-center text-slate-500">{t('common.loading')}</p>;
  if (!data || data.nights.length === 0)
    return <p className="card text-center text-sm text-slate-500">{t('trend.noData')}</p>;

  const rows = data.nights.map((n: TrendNight) => ({
    date: shortDate(n.started_at),
    events: n.n_events ?? 0,
    sfi: n.sfi_max_s != null ? Number((n.sfi_max_s / 60).toFixed(1)) : 0,
    supine: n.supine_burden != null ? Number((n.supine_burden * 100).toFixed(0)) : 0,
  }));

  const actionsByDate = new Map<string, number>();
  for (const a of data.care_actions) {
    const key = shortDate(a.performed_at);
    actionsByDate.set(key, (actionsByDate.get(key) ?? 0) + 1);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{t('trend.title')}</h2>
        <div className="flex gap-2">
          {[7, 30].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setNights(n)}
              className={nights === n ? 'btn-primary py-1' : 'btn-ghost py-1'}
            >
              {t(n === 7 ? 'trend.7' : 'trend.30')}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <h3 className="mb-1 text-sm font-medium">{t('trend.events')}</h3>
        <TrendLine data={rows} dataKey="events" label={t('trend.events')} />
      </div>
      <div className="card">
        <h3 className="mb-1 text-sm font-medium">{t('trend.sfi')}</h3>
        <TrendLine data={rows} dataKey="sfi" label={t('trend.sfi')} color="#f59e0b" />
      </div>
      <div className="card">
        <h3 className="mb-1 text-sm font-medium">{t('trend.supine')}</h3>
        <TrendLine data={rows} dataKey="supine" label={t('trend.supine')} color="#8b5cf6" />
      </div>

      <div className="card">
        <h3 className="mb-2 text-sm font-medium">{t('trend.actions')}</h3>
        <div className="flex flex-wrap gap-2">
          {rows.map((r: (typeof rows)[number]) => {
            const count = actionsByDate.get(r.date) ?? 0;
            return (
              <span
                key={r.date}
                className={`rounded-md px-2 py-1 text-xs ${
                  count > 0
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200'
                    : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                }`}
              >
                {r.date} {count > 0 ? `· ${count}` : ''}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
