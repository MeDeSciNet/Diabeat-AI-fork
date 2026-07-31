import { useCallback, useState } from 'react';

import type { SwallowEvent } from '@somno/types';
import { NightChart } from '@shared/components/Charts';
import { api } from '@shared/lib/api';
import { msToClock } from '@shared/lib/format';
import { useApi } from '@shared/lib/useApi';
import { useI18n } from '@shared/lib/useI18n';

import { getSubjectCode } from '../lib/subject';

/** C-2 overnight timeline: stage ribbon, posture ribbon, signal, event markers. */
export default function Timeline() {
  const { t } = useI18n();
  const subject = getSubjectCode();
  const [selected, setSelected] = useState<SwallowEvent | null>(null);

  const load = useCallback(async () => {
    const sessions = await api.sessions(subject);
    const latest = sessions.find((s) => s.status === 'analyzed') ?? sessions[0];
    if (!latest) return null;
    return api.timeline(latest.id, 900);
  }, [subject]);

  const { data, loading, error } = useApi(load, [subject]);

  if (loading) return <p className="py-10 text-center text-slate-500">{t('common.loading')}</p>;
  if (error || !data)
    return <p className="py-10 text-center text-slate-500">{t('home.noSession')}</p>;

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">{t('timeline.title')}</h2>
      <div className="card">
        <NightChart
          timeline={data}
          onSelectEvent={(id: string) =>
            setSelected(data.events.find((e: SwallowEvent) => e.id === id) ?? null)
          }
        />
      </div>

      {selected && (
        <div className="card">
          <div className="flex items-start justify-between">
            <h3 className="font-medium">{msToClock(selected.t_start_ms)}</h3>
            <button type="button" className="btn-ghost py-1" onClick={() => setSelected(null)}>
              ✕
            </button>
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <Field label={t('event.confidence')} value={(selected.confidence * 100).toFixed(0) + '%'} />
            <Field label={t('event.pattern')} value={selected.coordination_pattern ?? '-'} />
            <Field label={t('event.stage')} value={selected.sleep_stage ?? '-'} />
            <Field label={t('event.posture')} value={selected.posture ?? '-'} />
            <Field
              label={t('event.apnea')}
              value={selected.swallow_apnea_ms ? `${selected.swallow_apnea_ms} ms` : '-'}
            />
            <Field label={t('event.arousal')} value={selected.arousal_linked ? '✓' : '-'} />
          </dl>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="label">{label}</dt>
      <dd className="mt-0.5 font-medium">{value}</dd>
    </div>
  );
}
