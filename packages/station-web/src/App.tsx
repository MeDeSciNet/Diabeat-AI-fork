import { NavLink, Navigate, Route, Routes } from 'react-router-dom';

import { RuoBadge, RuoFooter } from '@shared/components/Ruo';
import { useI18n } from '@shared/lib/useI18n';
import type { Lang } from '@shared/lib/i18n';

import BedDetail from './pages/BedDetail';
import Beds from './pages/Beds';
import Health from './pages/Health';
import Queue from './pages/Queue';
import Shift from './pages/Shift';

const TABS = [
  { to: '/beds', key: 'nav.beds' as const },
  { to: '/shift', key: 'nav.shift' as const },
  { to: '/queue', key: 'nav.queue' as const },
  { to: '/health', key: 'nav.health' as const },
];

export default function App() {
  const { t, lang, setLang } = useI18n();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="no-print sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
        <div className="mx-auto flex max-w-[1800px] items-center gap-6 px-6 py-3">
          <h1 className="text-lg font-semibold">{t('app.station')}</h1>
          <nav className="flex gap-1">
            {TABS.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm ${
                    isActive
                      ? 'bg-sky-100 font-semibold text-sky-800 dark:bg-sky-900/60 dark:text-sky-200'
                      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                  }`
                }
              >
                {t(tab.key)}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <button
              type="button"
              className="text-xs text-slate-500 hover:underline"
              onClick={() => setLang(lang === 'zh-Hant' ? 'en' : ('zh-Hant' as Lang))}
            >
              {lang === 'zh-Hant' ? 'EN' : '中文'}
            </button>
            <RuoBadge />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1800px] flex-1 px-6 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/beds" replace />} />
          <Route path="/beds" element={<Beds />} />
          <Route path="/beds/:bedId" element={<BedDetail />} />
          <Route path="/shift" element={<Shift />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/health" element={<Health />} />
          <Route path="*" element={<Navigate to="/beds" replace />} />
        </Routes>
      </main>

      <RuoFooter />
    </div>
  );
}
