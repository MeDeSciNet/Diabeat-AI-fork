import { useCallback, useState } from 'react';

import { api } from '@shared/lib/api';
import { useApi } from '@shared/lib/useApi';
import { useI18n } from '@shared/lib/useI18n';

import { ACTOR_ID, getBedId } from '../lib/subject';

/**
 * C-4 mattress control.
 *
 * Everything on this screen is either a manual control the caregiver operates
 * directly, or a suggestion with a confirm button. There is no path from a
 * detection to a motion (PRD 2.1 R2) - the "confirm" button is the only thing
 * that starts a movement, and the safety envelope is stated on screen so the
 * limits are not a surprise when a command is refused.
 */
export default function Mattress() {
  const { t } = useI18n();
  const bedId = getBedId();
  const [hob, setHob] = useState(30);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(
    async () => ({
      state: await api.mattressState(bedId),
      advisories: await api.advisories(bedId),
    }),
    [bedId],
  );
  const { data, loading, error, reload } = useApi(load, [bedId]);

  if (loading) return <p className="py-10 text-center text-slate-500">{t('common.loading')}</p>;
  if (error || !data)
    return <p className="card text-center text-sm text-slate-500">{t('mattress.none')}</p>;

  const { state, advisories } = data;
  type Advisory = (typeof advisories)[number];
  const pending = advisories.filter((a: Advisory) => a.status === 'pending');

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setMessage(null);
    try {
      await fn();
      setMessage(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
      reload();
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">{t('mattress.title')}</h2>

      {!state.link_ok && (
        <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          {t('mattress.linkDown')}
        </p>
      )}

      <section className="card">
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="label">{t('mattress.hob')}</dt>
            <dd className="mt-0.5 text-2xl font-semibold">{state.hob_angle_deg.toFixed(0)}°</dd>
          </div>
          <div>
            <dt className="label">{t('mattress.lateral')}</dt>
            <dd className="mt-0.5 text-2xl font-semibold">
              {state.lateral_side} {state.lateral_deg.toFixed(0)}°
            </dd>
          </div>
          <div>
            <dt className="label">{t('mattress.mode')}</dt>
            <dd className="mt-0.5 font-medium">{t(`mattress.mode.${state.mode}` as never)}</dd>
          </div>
          <div>
            <dt className="label">{t('mattress.occupied')}</dt>
            <dd className="mt-0.5 font-medium">
              {state.occupied ? t('mattress.occupied') : t('mattress.unoccupied')}
              {state.moving ? ` · ${t('mattress.moving')}` : ''}
            </dd>
          </div>
        </dl>
      </section>

      <section className="card">
        <h3 className="mb-1 text-sm font-semibold">{t('mattress.advisories')}</h3>
        <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
          {t('mattress.confirmNotice')}
        </p>
        {pending.length === 0 ? (
          <p className="text-sm text-slate-500">{t('mattress.noAdvisories')}</p>
        ) : (
          <ul className="space-y-3">
            {pending.map((adv: Advisory) => (
              <li key={adv.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-sm font-medium">{adv.reason}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {adv.action} · {JSON.stringify(adv.params)}
                </p>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={busy != null}
                    onClick={() => run('confirm', () => api.confirmAdvisory(bedId, adv.id, ACTOR_ID))}
                  >
                    {t('mattress.confirm')}
                  </button>
                  <button
                    type="button"
                    className="btn-ghost"
                    disabled={busy != null}
                    onClick={() => run('decline', () => api.declineAdvisory(bedId, adv.id, ACTOR_ID))}
                  >
                    {t('mattress.decline')}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card space-y-4">
        <div>
          <label htmlFor="hob" className="label">
            {t('mattress.hob')}: {hob}°
          </label>
          <input
            id="hob"
            type="range"
            min={0}
            max={45}
            step={5}
            value={hob}
            onChange={(e) => setHob(Number(e.target.value))}
            className="mt-2 w-full accent-sky-600"
          />
          <button
            type="button"
            className="btn-primary mt-2 w-full"
            disabled={busy != null || !state.occupied || !state.link_ok}
            onClick={() =>
              run('hob', () =>
                api.mattressCommand(bedId, {
                  type: 'set_hob_angle',
                  params: { deg: hob },
                  actor_id: ACTOR_ID,
                }),
              )
            }
          >
            {t('mattress.apply')}
          </button>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {(['left', 'flat', 'right'] as const).map((side) => (
            <button
              key={side}
              type="button"
              className="btn-ghost"
              disabled={busy != null || !state.occupied || !state.link_ok}
              onClick={() =>
                run('lateral', () =>
                  api.mattressCommand(bedId, {
                    type: 'set_lateral_tilt',
                    params: { side, deg: side === 'flat' ? 0 : 20 },
                    actor_id: ACTOR_ID,
                  }),
                )
              }
            >
              {side}
            </button>
          ))}
        </div>

        <div>
          <span className="label">{t('mattress.schedule')}</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {[120, 180, 240].map((min) => (
              <button
                key={min}
                type="button"
                className={
                  state.schedule?.interval_min === min && state.schedule?.enabled
                    ? 'btn-primary py-1'
                    : 'btn-ghost py-1'
                }
                disabled={busy != null}
                onClick={() =>
                  run('schedule', async () => {
                    await api.mattressMode(bedId, 'scheduled', ACTOR_ID);
                    await api.mattressSchedule(bedId, true, min, ACTOR_ID);
                  })
                }
              >
                {min} {t('mattress.scheduleMin')}
              </button>
            ))}
            <button
              type="button"
              className={!state.schedule?.enabled ? 'btn-primary py-1' : 'btn-ghost py-1'}
              disabled={busy != null}
              onClick={() => run('manual', () => api.mattressMode(bedId, 'manual', ACTOR_ID))}
            >
              {t('mattress.mode.manual')}
            </button>
          </div>
        </div>
      </section>

      <section className="card border-rose-200 dark:border-rose-900">
        <button
          type="button"
          className="btn w-full bg-rose-600 text-white hover:bg-rose-700"
          disabled={busy != null}
          onClick={() => run('flat', () => api.mattressEmergencyFlat(bedId, ACTOR_ID))}
        >
          {t('mattress.emergencyFlat')}
        </button>
        <p className="mt-2 text-center text-xs text-slate-500">{t('mattress.emergencyHint')}</p>
      </section>

      {message && (
        <p className="rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-900">
          {message}
        </p>
      )}

      <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        {t('mattress.safetyNotice')}
      </p>
    </div>
  );
}
