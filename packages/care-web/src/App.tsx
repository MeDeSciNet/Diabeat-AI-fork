import { NavLink, Navigate, Route, Routes } from 'react-router-dom';

import { RuoBadge, RuoFooter } from '@shared/components/Ruo';
import { useI18n } from '@shared/lib/useI18n';

import Home from './pages/Home';
import Mattress from './pages/Mattress';
import Settings from './pages/Settings';
import Timeline from './pages/Timeline';
import Trend from './pages/Trend';

const TABS = [
  { to: '/home', key: 'nav.home' as const, icon: '🌙' },
  { to: '/timeline', key: 'nav.timeline' as const, icon: '📈' },
  { to: '/trend', key: 'nav.trend' as const, icon: '📊' },
  { to: '/mattress', key: 'nav.mattress' as const, icon: '🛏️' },
  { to: '/settings', key: 'nav.settings' as const, icon: '⚙️' },
];

export default function App() {
  const { t } = useI18n();
  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
        <h1 className="text-base font-semibold">{t('app.care')}</h1>
        <RuoBadge />
      </header>

      <main className="flex-1 px-4 pb-24 pt-4">
        <Routes>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<Home />} />
          <Route path="/timeline" element={<Timeline />} />
          <Route path="/trend" element={<Trend />} />
          <Route path="/mattress" element={<Mattress />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/home" replace />} />
        </Routes>
      </main>

      <RuoFooter />

      <nav className="fixed inset-x-0 bottom-0 mx-auto flex max-w-2xl border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] dark:border-slate-800 dark:bg-slate-950">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] ${
                isActive
                  ? 'font-semibold text-sky-600 dark:text-sky-400'
                  : 'text-slate-500 dark:text-slate-400'
              }`
            }
          >
            <span aria-hidden className="text-lg leading-none">
              {tab.icon}
            </span>
            {t(tab.key)}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
