"use client"

import * as React from "react"
import {
  CheckCircle2,
  ChevronDown,
  Flame,
  RefreshCcw,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  StreakCalendar,
  type StreakPeriod,
} from "@/components/ui/streak-calendar"

interface StreakCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Streak periods passed through to StreakCalendar */
  streak: StreakPeriod[]
  /** Current streak value in days */
  currentStreak: number
  /** Longest streak value in days */
  longestStreak: number
  /** Secondary total metric value */
  total: number
  /** Optional heading text */
  title?: string
  /** Label for the action button */
  actionLabel?: string
  /** Callback for action click */
  onActionClick?: () => void
  /** Show "How streaks work" dropdown section */
  showHowItWorks?: boolean
  /** Title for the dropdown trigger */
  howItWorksTitle?: string
  /** Content rows shown when the dropdown is expanded */
  howItWorksItems?: string[]
  /** Initial expanded state for dropdown */
  defaultHowItWorksOpen?: boolean
  /** Datas neutras (folga ou fim de semana) repassadas ao calendário */
  neutralDates?: string[]
}

const workdays = (n: number) => (n === 1 ? "dia útil" : "dias úteis")

const StreakCard = React.forwardRef<HTMLDivElement, StreakCardProps>(
  (
    {
      className,
      streak,
      currentStreak,
      longestStreak,
      total,
      title = "Sequência",
      actionLabel = "Ver calendário",
      onActionClick,
      showHowItWorks = true,
      howItWorksTitle = "Como funciona a sequência?",
      howItWorksItems = [
        "Um dia útil conta quando você estuda ao menos 30 minutos.",
        "Fim de semana e folgas declaradas não quebram nem somam.",
        "Cada semana completa rende 1 congelamento (máx. 2), que cobre um dia útil perdido.",
      ],
      defaultHowItWorksOpen = false,
      neutralDates,
      ...props
    },
    ref
  ) => {
    const [isHowItWorksOpen, setIsHowItWorksOpen] = React.useState(
      defaultHowItWorksOpen
    )
    const howItWorksContentId = React.useId()

    return (
      <section
        ref={ref}
        aria-label="Resumo da sequência"
        className={cn("bg-card rounded-2xl border p-6 shadow-sm", className)}
        {...props}
      >
        <header className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Flame className="text-primary h-6 w-6" aria-hidden="true" />
            <h3 className="text-2xl leading-none font-semibold">{title}</h3>
          </div>
          <Button
            variant="link"
            size="sm"
            onClick={onActionClick}
            aria-label={actionLabel}
            className="text-muted-foreground hover:text-foreground text-sm font-medium transition-colors"
          >
            {actionLabel}
          </Button>
        </header>

        <p className="mb-4 text-5xl leading-none font-semibold tracking-tight">
          {currentStreak}
          <span className="text-muted-foreground ml-2 text-2xl font-medium">
            {workdays(currentStreak)}
          </span>
        </p>

        <StreakCalendar
          streak={streak}
          view="week"
          startOfWeek={1}
          neutralDates={neutralDates}
          className="max-w-none"
        />

        <div
          className="mt-4 grid grid-cols-2 gap-4 border-t border-dashed pt-4"
          aria-label="Números da sequência"
        >
          <div>
            <p className="text-muted-foreground text-sm">Recorde</p>
            <p className="text-3xl leading-tight font-semibold">
              {longestStreak}
              <span className="ml-1 text-2xl font-medium">{workdays(longestStreak)}</span>
            </p>
          </div>
          <div className="text-right">
            <p className="text-muted-foreground text-sm">Congelamentos</p>
            <p className="text-3xl leading-tight font-semibold">{total}</p>
          </div>
        </div>

        {showHowItWorks && (
          <div className="mt-4 border-t pt-4">
            <button
              type="button"
              className="bg-muted flex w-full items-center justify-between rounded-xl px-4 py-3 text-left"
              onClick={() => setIsHowItWorksOpen((prev) => !prev)}
              aria-expanded={isHowItWorksOpen}
              aria-controls={howItWorksContentId}
            >
              <span className="text-lg font-semibold">{howItWorksTitle}</span>
              <ChevronDown
                className={cn(
                  "text-muted-foreground h-5 w-5 transition-transform",
                  isHowItWorksOpen && "rotate-180"
                )}
                aria-hidden="true"
              />
            </button>

            {isHowItWorksOpen && (
              <div id={howItWorksContentId} className="space-y-4 px-2 pt-4">
                {howItWorksItems.map((item, index) => {
                  const Icon =
                    index === 0
                      ? CheckCircle2
                      : index === 1
                        ? Flame
                        : RefreshCcw
                  return (
                    <div
                      key={`${item}-${index}`}
                      className="flex items-start gap-3"
                    >
                      <Icon
                        className="text-primary mt-0.5 h-5 w-5 shrink-0"
                        aria-hidden="true"
                      />
                      <p className="text-muted-foreground text-lg leading-snug">
                        {item}
                      </p>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </section>
    )
  }
)
StreakCard.displayName = "StreakCard"

export { StreakCard }
export type { StreakCardProps }
