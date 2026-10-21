import { BookOpen, CalendarDays, Ellipsis, House, Layers, RotateCcw, Settings, Trophy } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'

import { CatalogPage } from '../features/catalog/CatalogPage'
import { CyclePage } from '../features/cycle/CyclePage'
import { FlashcardsPage } from '../features/flashcards/FlashcardsPage'
import { ProgressPage } from '../features/progress/ProgressPage'
import { ReviewSessionRoute } from '../features/reviews/ReviewSession'
import { ReviewsPage } from '../features/reviews/ReviewsPage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { TodayPage } from '../features/today/TodayPage'
import { Hud } from './Hud'

/** `mobile`: onde o link aparece no celular — na barra, no menu "Mais" ou fora (Config. é a engrenagem do Hud). */
const LINKS = [
  { to: '/', label: 'Hoje', icon: House, mobile: 'bar' },
  { to: '/ciclo', label: 'Ciclo', icon: CalendarDays, mobile: 'bar' },
  { to: '/revisoes', label: 'Revisões', icon: RotateCcw, mobile: 'bar' },
  { to: '/edital', label: 'Edital', icon: BookOpen, mobile: 'bar' },
  { to: '/cartoes', label: 'Cartões', icon: Layers, mobile: 'more' },
  { to: '/progresso', label: 'Progresso', icon: Trophy, mobile: 'more' },
  { to: '/config', label: 'Config.', icon: Settings, mobile: 'hud' },
] as const

const linkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'touch-target flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-0 py-1.5 text-center text-sm leading-tight tracking-tight [overflow-wrap:anywhere]',
    'font-medium transition-colors',
    'md:flex-none md:flex-row md:gap-3 md:px-3 md:py-3 md:text-base',
    isActive
      ? 'text-primary md:border-r-2 md:border-primary'
      : 'text-muted-foreground hover:text-foreground',
  ].join(' ')

export function App() {
  return (
    <div className="md:flex">
      <nav aria-label="Principal" className="fixed inset-x-0 bottom-0 z-40 flex border-t border-border bg-card pb-[env(safe-area-inset-bottom)]
        md:sticky md:top-0 md:h-screen md:w-56 md:flex-col md:border-r md:border-t-0 md:bg-background md:py-6 md:pl-4">
        <p className="hidden pb-8 pl-3 font-pixel text-xl text-primary md:block">CGU 2026</p>
        {LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.to === '/'}
            className={(state) => `${linkClass(state)}${l.mobile === 'bar' ? '' : ' max-md:hidden'}`}>
            <l.icon className="size-5" aria-hidden="true" />
            {l.label}
          </NavLink>
        ))}
        <MoreMenu />
      </nav>
      <div className="min-h-screen flex-1 pb-[calc(5rem+env(safe-area-inset-bottom))] md:pb-0">
        <Hud />
        <main className="mx-auto max-w-3xl p-4 md:p-8">
          <Routes>
            <Route path="/" element={<TodayPage />} />
            <Route path="/ciclo" element={<CyclePage />} />
            <Route path="/revisoes" element={<ReviewsPage />} />
            <Route path="/revisoes/:id" element={<ReviewSessionRoute />} />
            <Route path="/edital" element={<CatalogPage />} />
            <Route path="/cartoes" element={<FlashcardsPage />} />
            <Route path="/progresso" element={<ProgressPage />} />
            <Route path="/config" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

/** Celular: links que não cabem na barra, num painel acima dela. Fecha ao navegar, ao tocar fora e com Esc. */
function MoreMenu() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  const items = LINKS.filter((l) => l.mobile === 'more')
  const active = items.some((l) => pathname.startsWith(l.to))
  useEffect(() => setOpen(false), [pathname])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  return (
    <div className="flex min-w-0 flex-1 md:hidden">
      <button type="button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}
        className={`${linkClass({ isActive: active || open })} md:hidden`}>
        <Ellipsis className="size-5" aria-hidden="true" />
        Mais
      </button>
      {open && (
        <>
          <button type="button" aria-label="Fechar menu" tabIndex={-1} className="fixed inset-0 -z-10 cursor-default"
            onClick={() => setOpen(false)} />
          <div role="menu" aria-label="Mais"
            className="absolute bottom-full right-2 mb-2 w-48 rounded-lg border border-border bg-card p-1 shadow-lg">
            {items.map((l) => (
              <NavLink key={l.to} to={l.to} role="menuitem"
                className={({ isActive }) => `touch-target flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
                  isActive ? 'text-primary' : 'text-foreground hover:bg-muted'}`}>
                <l.icon className="size-5" aria-hidden="true" />
                {l.label}
              </NavLink>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

