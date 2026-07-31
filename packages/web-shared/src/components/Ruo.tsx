import { useI18n } from '../lib/useI18n';

/**
 * The research-use notice. Present on every screen in both apps (PRD 7.2, 12).
 * Rendered as a persistent footer rather than a dismissible banner, because a
 * notice the user can close is a notice that is usually closed.
 */
export function RuoFooter() {
  const { t } = useI18n();
  return (
    <footer className="mt-10 border-t border-slate-200 bg-slate-50 px-4 py-3 text-center text-xs leading-relaxed text-slate-500 print:mt-4 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-400">
      {t('ruo.notice')}
    </footer>
  );
}

export function RuoBadge() {
  const { t } = useI18n();
  return (
    <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-300">
      {t('ruo.short')}
    </span>
  );
}
