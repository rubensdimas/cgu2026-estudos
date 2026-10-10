import { NavLink, Route, Routes } from 'react-router-dom'

import { CatalogPage } from '../features/catalog/CatalogPage'
import { CyclePage } from '../features/cycle/CyclePage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { TodayPage } from '../features/today/TodayPage'
import { Hud } from './Hud'

const LINKS = [
  { to: '/', label: 'Hoje' },
  { to: '/ciclo', label: 'Ciclo' },
  { to: '/edital', label: 'Edital' },
  { to: '/config', label: 'Config.' },
]

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-semibold ${isActive ? 'bg-muted text-xp' : 'text-muted-foreground hover:text-foreground'}`

export function App() {
  return (
    <div className="md:flex">
      <nav aria-label="Principal" className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-border bg-card
        md:static md:h-screen md:w-48 md:flex-col md:justify-start md:gap-1 md:border-r md:border-t-0 md:p-4">
        <p className="hidden pb-4 font-pixel text-xl text-primary md:block">CGU 2026</p>
        {LINKS.map((l) => <NavLink key={l.to} to={l.to} end className={linkClass}>{l.label}</NavLink>)}
      </nav>
      <div className="min-h-screen flex-1 pb-20 md:pb-0">
        <Hud />
        <main className="mx-auto max-w-3xl p-4">
          <Routes>
            <Route path="/" element={<TodayPage />} />
            <Route path="/ciclo" element={<CyclePage />} />
            <Route path="/edital" element={<CatalogPage />} />
            <Route path="/config" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
