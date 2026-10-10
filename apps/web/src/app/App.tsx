import { BookOpen, CalendarDays, House, Settings, Trophy } from 'lucide-react'
import { NavLink, Route, Routes } from 'react-router-dom'

import { CatalogPage } from '../features/catalog/CatalogPage'
import { CyclePage } from '../features/cycle/CyclePage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { TodayPage } from '../features/today/TodayPage'
import { Hud } from './Hud'

const LINKS = [
  { to: '/', label: 'Hoje', icon: House },
  { to: '/ciclo', label: 'Ciclo', icon: CalendarDays },
  { to: '/edital', label: 'Edital', icon: BookOpen },
  { to: '/progresso', label: 'Progresso', icon: Trophy },
  { to: '/config', label: 'Config.', icon: Settings },
]

const linkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'flex flex-1 flex-col items-center gap-1 px-2 py-2 text-xs font-medium transition-colors',
    'md:flex-none md:flex-row md:gap-3 md:px-3 md:py-3 md:text-base',
    isActive
      ? 'text-primary md:border-r-2 md:border-primary'
      : 'text-muted-foreground hover:text-foreground',
  ].join(' ')

export function App() {
  return (
    <div className="md:flex">
      <nav aria-label="Principal" className="fixed inset-x-0 bottom-0 z-40 flex border-t border-border bg-card
        md:sticky md:top-0 md:h-screen md:w-56 md:flex-col md:border-r md:border-t-0 md:bg-background md:py-6 md:pl-4">
        <p className="hidden pb-8 pl-3 font-pixel text-xl text-primary md:block">CGU 2026</p>
        {LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} end className={linkClass}>
            <l.icon className="size-5" aria-hidden="true" />
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="min-h-screen flex-1 pb-20 md:pb-0">
        <Hud />
        <main className="mx-auto max-w-3xl p-4 md:p-8">
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
