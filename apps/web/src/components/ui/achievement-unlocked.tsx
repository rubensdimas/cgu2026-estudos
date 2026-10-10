"use client"

import * as React from "react"
import { CalendarDays, Share2, X } from "lucide-react"
import { Dialog as DialogPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"
import {
  AchievementBadge,
  type UserAchievement,
} from "@/components/ui/achievement-badge"
import { Button } from "@/components/ui/button"

// Types (inlined - only fields used by this component)
interface Achievement {
  id: string
  name: string
  trigger?: "metric" | "api" | "streak"
  description?: string | null
  unlockedAt?: string
}

// Props
interface AchievementUnlockedProps {
  /** Achievement that was unlocked */
  achievement: Achievement
  /** Control open state */
  open: boolean
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void
  /** Label for the secondary action button */
  secondaryActionLabel?: string
  /** Callback for the secondary action button (e.g. social share) */
  onSecondaryActionClick?: () => void
  /** @deprecated Use onSecondaryActionClick instead */
  onShare?: () => void
  /** Custom class for the dialog */
  className?: string
}

const AchievementUnlocked = React.forwardRef<
  HTMLDivElement,
  AchievementUnlockedProps
>(
  (
    {
      achievement,
      open,
      onOpenChange,
      secondaryActionLabel = "Compartilhar",
      onSecondaryActionClick,
      onShare,
      className,
    },
    ref
  ) => {
    const handleSecondaryActionClick = onSecondaryActionClick ?? onShare
    const continueRef = React.useRef<HTMLButtonElement>(null)
    const unlockedDateLabel = React.useMemo(() => {
      const input = achievement.unlockedAt ?? new Date().toISOString()
      const date = new Date(input)
      if (Number.isNaN(date.getTime())) return "Conquistado hoje"
      return `Conquistado em ${date.toLocaleDateString("pt-BR", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })}`
    }, [achievement.unlockedAt])

    const badgeAchievement = React.useMemo<UserAchievement>(() => {
      return {
        id: achievement.id,
        name: achievement.name,
        trigger: achievement.trigger ?? "streak",
        achievedAt: achievement.unlockedAt ?? new Date().toISOString(),
      }
    }, [achievement])

    // Radix Dialog cuida de foco preso, foco inicial, restauração do foco, Esc e trava de rolagem.
    return (
      <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/70" />
          <DialogPrimitive.Content
            ref={ref}
            onOpenAutoFocus={(e) => {
              e.preventDefault()
              continueRef.current?.focus()
            }}
            className={cn(
              "fixed top-1/2 left-1/2 z-50 -translate-x-1/2 -translate-y-1/2",
              "bg-card max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-md overflow-y-auto rounded-xl border p-6 shadow-2xl",
              className
            )}
          >
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Fechar" className="absolute top-4 right-4">
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </DialogPrimitive.Close>

            <div className="flex flex-col items-center text-center">
              <div aria-hidden="true">
                <AchievementBadge
                  achievement={badgeAchievement}
                  badgeSize="xl"
                  className="mt-8 mb-12 border-0 bg-transparent p-0 shadow-none hover:shadow-none [&>span:last-child]:hidden"
                />
              </div>

              <span className="text-muted-foreground mb-4 inline-flex items-center gap-1 rounded-full border px-3 py-1 text-sm">
                <CalendarDays className="h-4 w-4" aria-hidden="true" />
                {unlockedDateLabel}
              </span>

              <DialogPrimitive.Title className="mb-2 text-4xl font-bold tracking-tight">
                {achievement.name}
              </DialogPrimitive.Title>

              {achievement.description ? (
                <DialogPrimitive.Description className="text-muted-foreground mb-3 text-lg">
                  {achievement.description}
                </DialogPrimitive.Description>
              ) : (
                <DialogPrimitive.Description className="sr-only">{achievement.name}</DialogPrimitive.Description>
              )}

              <div className="mt-8 flex gap-3">
                {handleSecondaryActionClick && (
                  <Button variant="outline" size="lg" onClick={handleSecondaryActionClick}>
                    <Share2 className="h-4 w-4" aria-hidden="true" />
                    {secondaryActionLabel}
                  </Button>
                )}
                <Button ref={continueRef} onClick={() => onOpenChange(false)}>
                  Continuar
                </Button>
              </div>
            </div>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>
    )
  }
)
AchievementUnlocked.displayName = "AchievementUnlocked"

export { AchievementUnlocked }
export type { AchievementUnlockedProps, Achievement }
