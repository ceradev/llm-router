import { useEffect, useId, useRef, useState, type ReactNode } from "react"

import { useI18n } from "@/contexts/I18nContext"
import { useTheme } from "@/contexts/ThemeContext"
import type { Locale } from "@/i18n/translations"
import { IconChevronDown, IconMoon, IconSun } from "./icons"

const LOCALE_OPTIONS: { code: Locale; triggerLabel: string; name: string }[] = [
  { code: "en", triggerLabel: "EN", name: "English" },
  { code: "es", triggerLabel: "ES", name: "Español" },
]

export function ThemeToggle() {
  const { t } = useI18n()
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="group relative inline-flex">
      <button
        type="button"
        onClick={toggleTheme}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) transition-colors hover:bg-(--surface-glass-hover) hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
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

export function LocaleSelector() {
  const { locale, setLocale } = useI18n()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const listId = useId()

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false)
    }
    document.addEventListener("pointerdown", onPointerDown)
    document.addEventListener("keydown", onKeyDown)
    return () => {
      document.removeEventListener("pointerdown", onPointerDown)
      document.removeEventListener("keydown", onKeyDown)
    }
  }, [open])

  const current =
    LOCALE_OPTIONS.find((o) => o.code === locale) ?? LOCALE_OPTIONS[0]
  const triggerClass =
    "flex h-10 min-w-[4.75rem] shrink-0 items-center justify-between gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-glass)] px-3 text-xs font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-glass-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)]"
  const itemClass = (active: boolean) =>
    `w-full px-3 py-2 text-left text-xs font-medium transition-colors first:rounded-t-[inherit] last:rounded-b-[inherit] ${
      active
        ? "bg-[#3B82F6]/20 text-[var(--text-accent)]"
        : "text-[var(--text-muted)] hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)]"
    }`

  const localeTooltip = locale === "es" ? "Idioma" : "Language"

  return (
    <div ref={rootRef} className="group relative inline-flex">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={listId}
        aria-label="Language"
        className={triggerClass}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-sm font-medium text-(--text-primary)">
          {current.triggerLabel}
        </span>
        <IconChevronDown
          className={`h-4 w-4 shrink-0 text-(--text-muted) transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open ? null : (
        <span className="pointer-events-none absolute left-1/2 top-[calc(100%+0.45rem)] z-60 -translate-x-1/2 rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2 py-1 text-[11px] font-medium whitespace-nowrap text-(--text-primary) opacity-0 shadow-lg backdrop-blur-md transition-all duration-150 group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100">
          {localeTooltip}
        </span>
      )}
      {open ? (
        <ul
          id={listId}
          aria-label="Language"
          className="absolute right-0 top-[calc(100%+0.25rem)] z-50 min-w-38 overflow-hidden rounded-lg border border-(--border-subtle) bg-(--surface-glass) py-0.5 shadow-lg backdrop-blur-sm"
        >
          {LOCALE_OPTIONS.map((opt) => (
            <li key={opt.code}>
              <button
                type="button"
                className={itemClass(locale === opt.code)}
                onClick={() => {
                  setLocale(opt.code)
                  setOpen(false)
                }}
              >
                <span className="inline-flex items-center gap-2">
                  <span className="inline-block min-w-5">
                    {opt.triggerLabel}
                  </span>
                  <span>{opt.name}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

/** Locale, theme, and history with spacing only (hero nav and fixed corners). */
export function NavbarToolbar({
  historySlot,
}: Readonly<{ historySlot: ReactNode }>) {
  return (
    <div className="flex items-center gap-3 sm:gap-4">
      <LocaleSelector />
      <ThemeToggle />
      {historySlot}
    </div>
  )
}

