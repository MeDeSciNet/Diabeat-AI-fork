import { api } from '@shared/lib/api';
import { dateTime } from '@shared/lib/format';
import { useApi } from '@shared/lib/useApi';
import { useI18n } from '@shared/lib/useI18n';

/** S-5 system health: device link, battery, storage, and data gaps. */
export default function Health() {
  const { t } = useI18n();
  const { data, loading } = useApi(() => api.systemHealth(), []);

  if (loading) return <p className="text-slate-500">{t('common.loading')}</p>;
  if (!data) return <p className="text-slate-500">{t('common.error')}</p>;

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-semibold">{t('health.title')}</h2>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label={t('health.sessions')} value={String(data.sessions_last_7d)} />
        <Stat label={t('health.failed')} value={String(data.sessions_failed)} />
        <Stat label={t('health.gaps')} value={String(data.data_gaps)} />
      </div>

      <section className="card">
        <h3 className="mb-3 text-sm font-semibold">{t('health.devices')}</h3>
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="py-1.5">Device</th>
              <th className="py-1.5">Bed</th>
              <th className="py-1.5">{t('health.lastSeen')}</th>
              <th className="py-1.5">{t('beds.battery')}</th>
              <th className="py-1.5">{t('health.storage')}</th>
              <th className="py-1.5">{t('health.electrode')}</th>
            </tr>
          </thead>
          <tbody>
            {data.devices.map((d: any) => (
              <tr key={d.device_id} className="border-t border-slate-100 dark:border-slate-800">
                <td className="py-1.5 font-mono text-xs">{d.device_id}</td>
                <td className="py-1.5">{d.bed_id ?? '-'}</td>
                <td className="py-1.5">
                  {dateTime(d.last_seen_at)}
                  {d.stale && (
                    <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[11px] text-amber-800 dark:bg-amber-900/50 dark:text-amber-200">
                      {t('health.stale')}
                    </span>
                  )}
                </td>
                <td className="py-1.5 tabular-nums">
                  {d.battery_pct != null ? `${d.battery_pct.toFixed(0)}%` : '-'}
                </td>
                <td className="py-1.5 tabular-nums">
                  {d.storage_free_pct != null ? `${d.storage_free_pct.toFixed(0)}%` : '-'}
                </td>
                <td className="py-1.5">
                  {d.electrode_ok == null
                    ? '-'
                    : d.electrode_ok
                      ? t('health.electrodeOk')
                      : t('health.electrodeOff')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <p className="label">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
