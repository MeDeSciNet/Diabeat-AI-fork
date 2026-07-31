import { useCallback, useState } from 'react';

import { api } from '@shared/lib/api';
import { dateTime } from '@shared/lib/format';
import { useApi } from '@shared/lib/useApi';
import { useI18n } from '@shared/lib/useI18n';

const SHIFTS = ['night', 'day', 'evening'] as const;

/**
 * S-2 shift summary.
 *
 * Export is browser print-to-PDF against a print stylesheet rather than a PDF
 * library: the output is a one-page handover sheet, and shipping a renderer to
 * produce it would be weight with no payoff.
 */
export default function Shift() {
  const { t } = useI18n();
  const [shift, setShift] = useState<(typeof SHIFTS)[number]>('day');
  const load = useCallback(() => api.shiftSummary(shift), [shift]);
  const { data, loading } = useApi(load, [shift]);

  return (
    <div className="space-y-4">
      <div className="no-print flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-semibold">{t('shift.title')}</h2>
        <div className="flex gap-2">
          {SHIFTS.map((s) => (
            <button
              key={s}
              type="button"
              className={shift === s ? 'btn-primary py-1' : 'btn-ghost py-1'}
              onClick={() => setShift(s)}
            >
              {t(`shift.${s}` as never)}
            </button>
          ))}
        </div>
        <button type="button" className="btn-ghost ml-auto" onClick={() => window.print()}>
          {t('shift.print')}
        </button>
      </div>

      <div className="hidden print:block">
        <h1 className="text-lg font-bold">
          {t('shift.title')} · {t(`shift.${shift}` as never)}
        </h1>
      </div>

      {loading && <p className="text-slate-500">{t('common.loading')}</p>}

      {data && (
        <>
          <p className="text-xs text-slate-500">
            {t('shift.generated')} {dateTime(data.generated_at)} · {data.window}
          </p>
          {data.beds.length === 0 ? (
            <p className="card text-sm text-slate-500">{t('shift.empty')}</p>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-300 text-left dark:border-slate-700">
                  <th className="py-2 pr-4">Bed</th>
                  <th className="py-2 pr-4">Subject</th>
                  <th className="py-2 pr-4">{t('home.suggestions')}</th>
                  <th className="py-2">Notes</th>
                </tr>
              </thead>
              <tbody>
                {data.beds.map((row: any) => (
                  <tr key={row.bed_id ?? row.subject_code} className="border-b border-slate-200 align-top dark:border-slate-800">
                    <td className="py-2 pr-4 font-semibold">{row.bed_id ?? '-'}</td>
                    <td className="py-2 pr-4">{row.subject_code}</td>
                    <td className="py-2 pr-4">
                      <ul className="list-inside list-disc space-y-0.5">
                        {row.actions.map((a: string) => (
                          <li key={a}>{t(`action.${a}` as never)}</li>
                        ))}
                      </ul>
                    </td>
                    <td className="py-2 text-xs text-slate-500">
                      {row.alerts.map((al: any) => (
                        <div key={al.id}>
                          {t(`common.severity.${al.severity}` as never)} · {al.title}
                        </div>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
