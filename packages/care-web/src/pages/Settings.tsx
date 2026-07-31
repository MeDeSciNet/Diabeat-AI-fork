import { useState } from 'react';

import { api } from '@shared/lib/api';
import { useApi } from '@shared/lib/useApi';
import type { Lang } from '@shared/lib/i18n';
import { useI18n } from '@shared/lib/useI18n';

import { getBedId, getSubjectCode, setBedId, setSubjectCode } from '../lib/subject';

/** C-5 settings: language, quiet hours, and which subject this device follows. */
export default function Settings() {
  const { t, lang, setLang } = useI18n();
  const [subject, setSubject] = useState(getSubjectCode());
  const [bed, setBed] = useState(getBedId());
  const { data: meta } = useApi(() => api.meta(), []);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">{t('settings.title')}</h2>

      <section className="card">
        <span className="label">{t('settings.language')}</span>
        <div className="mt-2 flex gap-2">
          {(['zh-Hant', 'en'] as Lang[]).map((code) => (
            <button
              key={code}
              type="button"
              className={lang === code ? 'btn-primary py-1' : 'btn-ghost py-1'}
              onClick={() => setLang(code)}
            >
              {code === 'zh-Hant' ? '繁體中文' : 'English'}
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <label className="label" htmlFor="subject">
          {t('settings.subject')}
        </label>
        <input
          id="subject"
          value={subject}
          onChange={(e) => {
            setSubject(e.target.value);
            setSubjectCode(e.target.value);
          }}
          className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
        />
        <label className="label mt-4 block" htmlFor="bed">
          Bed
        </label>
        <input
          id="bed"
          value={bed}
          onChange={(e) => {
            setBed(e.target.value);
            setBedId(e.target.value);
          }}
          className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
        />
      </section>

      <section className="card">
        <span className="label">{t('settings.quietHours')}</span>
        <p className="mt-2 text-sm">22:00 – 07:00</p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t('settings.quietHint')}</p>
      </section>

      <section className="card">
        <span className="label">{t('settings.about')}</span>
        <dl className="mt-2 space-y-1 text-sm">
          <div className="flex justify-between">
            <dt className="text-slate-500">detector</dt>
            <dd className="font-mono text-xs">{meta?.detector_version ?? '-'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">index</dt>
            <dd className="font-mono text-xs">{meta?.risk_version ?? '-'}</dd>
          </div>
        </dl>
        <p className="mt-3 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
          {t('index.explain')}
        </p>
      </section>
    </div>
  );
}
