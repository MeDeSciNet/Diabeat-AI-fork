import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '@shared/lib/api';
import { LIGHT_CLASS, pct } from '@shared/lib/format';
import { useApi, usePolling } from '@shared/lib/useApi';
import { useI18n } from '@shared/lib/useI18n';

/**
 * S-1 bed overview.
 *
 * Three status lights and no red. Red on a ward display means "go now", which
 * would make this an active patient monitor - the one thing PRD 2.1 R1 rules
 * out. Amber is as far up as the scale goes, and it means "there is something
 * to look at when you get there".
 */
export default function Beds() {
  const { t } = useI18n();
  const [wall, setWall] = useState(false);
  const [page, setPage] = useState(0);

  const { data, reload } = useApi(() => api.beds(), []);
  usePolling(useCallback(() => reload(), [reload]), 30_000);
  usePolling(
    useCallback(() => {
      if (wall) setPage((p) => p + 1);
    }, [wall]),
    20_000,
  );

  const beds = data ?? [];
  const perPage = wall ? 12 : beds.length || 1;
  const pages = Math.max(1, Math.ceil(beds.length / perPage));
  const shown = wall ? beds.slice((page % pages) * perPage, (page % pages) * perPage + perPage) : beds;

  return (
    <div className="space-y-4">
      <div className="no-print flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">{t('beds.title')}</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">{t('beds.sortNote')}</p>
        </div>
        <button type="button" className="btn-ghost" onClick={() => setWall((w) => !w)}>
          {wall ? t('beds.exitWall') : t('beds.wall')}
        </button>
      </div>

      <div
        className={`grid gap-4 ${
          wall
            ? 'grid-cols-2 md:grid-cols-3 xl:grid-cols-4'
            : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6'
        }`}
      >
        {shown.map((bed) => (
          <Link
            key={bed.bed_id}
            to={`/beds/${bed.bed_id}`}
            className="card transition-shadow hover:shadow-md"
          >
            <div className="flex items-center justify-between">
              <span className={wall ? 'text-3xl font-bold' : 'text-lg font-semibold'}>
                {bed.bed_id}
              </span>
              <span
                className={`inline-block rounded-full ${wall ? 'h-6 w-6' : 'h-4 w-4'} ${
                  LIGHT_CLASS[bed.light]
                }`}
                title={t(`light.${bed.light}` as never)}
              />
            </div>
            <p className={`mt-1 text-slate-500 ${wall ? 'text-base' : 'text-xs'}`}>
              {bed.subject_code ?? '-'} · {bed.ward ?? '-'}
            </p>
            <p className={`mt-2 ${wall ? 'text-xl' : 'text-sm'} font-medium`}>
              {t(`light.${bed.light}` as never)}
            </p>
            <dl className={`mt-3 space-y-1 ${wall ? 'text-base' : 'text-xs'} text-slate-500`}>
              <div className="flex justify-between">
                <dt>{t('beds.coverage')}</dt>
                <dd>{pct(bed.signal_coverage)}</dd>
              </div>
              <div className="flex justify-between">
                <dt>{t('beds.battery')}</dt>
                <dd>{bed.battery_pct != null ? `${bed.battery_pct.toFixed(0)}%` : '-'}</dd>
              </div>
            </dl>
            {bed.unacknowledged_alerts > 0 && (
              <p className="mt-3 rounded-md bg-amber-100 px-2 py-1 text-center text-xs font-semibold text-amber-800 dark:bg-amber-900/50 dark:text-amber-200">
                {bed.unacknowledged_alerts} {t('beds.unack')}
              </p>
            )}
            {!bed.session_id && (
              <p className="mt-3 text-xs text-slate-400">{t('beds.noSession')}</p>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
