import { type ReactNode } from "react"

import { useBackgroundMotion } from "@/contexts/BackgroundMotionContext"
import { useI18n } from "@/contexts/I18nContext"
import { useTheme } from "@/contexts/ThemeContext"
import type { Locale } from "@/i18n/translations"
import { IconMoon, IconSun } from "./icons"

export function ThemeToggle() {
  const { t } = useI18n()
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="group relative inline-flex">
      <button
        type="button"
        onClick={toggleTheme}
        className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-lg border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) transition-colors hover:bg-(--surface-glass-hover) hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
        aria-label={t("toggleTheme")}
      >
        {theme === "dark" ? (
          <IconSun className="h-5 w-5" />
        ) : (
          <IconMoon className="h-5 w-5" />
        )}
      </button>
      <span className="pointer-events-none absolute left-1/2 top-[calc(100%+0.45rem)] z-60 -translate-x-1/2 rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2 py-1 text-[11px] font-medium whitespace-nowrap text-(--text-primary) opacity-0 shadow-lg backdrop-blur-md transition-all duration-150 group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100">
        {t("toggleTheme")}
      </span>
    </div>
  )
}

export function BackgroundMotionToggle() {
  const { enabled, toggle } = useBackgroundMotion()

  const label = enabled ? "Background animation: on" : "Background animation: off"
  const short = enabled ? "FX" : "FX×"

  return (
    <div className="group relative inline-flex">
      <button
        type="button"
        onClick={toggle}
        className="flex h-11 w-11 cursor-pointer shrink-0 items-center justify-center rounded-lg border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) transition-colors hover:bg-(--surface-glass-hover) hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
        aria-label={label}
      >
        <span className="text-xs font-extrabold tracking-tight">{short}</span>
      </button>
      <span className="pointer-events-none absolute left-1/2 top-[calc(100%+0.45rem)] z-60 -translate-x-1/2 rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2 py-1 text-[11px] font-medium whitespace-nowrap text-(--text-primary) opacity-0 shadow-lg backdrop-blur-md transition-all duration-150 group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100">
        {label}
      </span>
    </div>
  )
}

export function LocaleSelector() {
  const { locale, setLocale } = useI18n()
  const localeTooltip = locale === "es" ? "Idioma" : "Language"

  return (
    <div className="group relative inline-flex">
      <div className="flex h-11 min-w-19 shrink-0 items-center gap-1 rounded-lg border border-(--border-subtle) bg-(--surface-glass) p-1">
        {(["en", "es"] as const).map((opt) => {
          const active = locale === opt
          return (
            <button
              key={opt}
              type="button"
              aria-pressed={active}
              className={
                active
                  ? "inline-flex h-9 min-w-8 items-center justify-center rounded-md bg-(--surface-glass-hover) px-2 text-xs font-semibold text-(--text-primary)"
                  : "inline-flex h-9 min-w-8 items-center justify-center rounded-md px-2 text-xs font-semibold text-(--text-muted) transition-colors hover:text-(--text-primary)"
              }
              onClick={() => setLocale(opt as Locale)}
            >
              {opt.toUpperCase()}
            </button>
          )
        })}
      </div>
      <span className="pointer-events-none absolute left-1/2 top-[calc(100%+0.45rem)] z-60 -translate-x-1/2 rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2 py-1 text-[11px] font-medium whitespace-nowrap text-(--text-primary) opacity-0 shadow-lg backdrop-blur-md transition-all duration-150 group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100">
        {localeTooltip}
      </span>
    </div>
  )
}

/** Locale, theme, and history with spacing only (hero nav and fixed corners). */
export function NavbarToolbar({
  historySlot,
}: Readonly<{
  historySlot?: ReactNode
}>) {
  return (
    <div className="flex shrink-0 items-center gap-1.5 sm:gap-3">
      <LocaleSelector />
      <BackgroundMotionToggle />
      <ThemeToggle />
      {historySlot}
    </div>
  )
}

