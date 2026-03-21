import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { useTheme } from '../../contexts/ThemeContext';
import type { Locale } from '../../i18n/translations';
import { IconChevronDown, IconMoon, IconSun } from '../shared/icons';

const LOCALE_OPTIONS: { code: Locale; label: string }[] = [
  { code: 'en', label: 'EN' },
  { code: 'es', label: 'ES' },
];

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-glass)] text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)]"
      aria-label="Toggle theme"
      title="Toggle theme"
    >
      {theme === 'dark' ? (
        <IconSun className="h-5 w-5" />
      ) : (
        <IconMoon className="h-5 w-5" />
      )}
    </button>
  );
}

export function LocaleSelector() {
  const { locale, setLocale } = useI18n();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const current = LOCALE_OPTIONS.find((o) => o.code === locale) ?? LOCALE_OPTIONS[0];
  const triggerClass =
    'flex h-10 min-w-[4.75rem] shrink-0 items-center justify-between gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-glass)] px-3 text-xs font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-glass-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)]';
  const itemClass = (active: boolean) =>
    `w-full px-3 py-2 text-left text-xs font-medium transition-colors first:rounded-t-[inherit] last:rounded-b-[inherit] ${
      active
        ? 'bg-[#3B82F6]/20 text-[var(--text-accent)]'
        : 'text-[var(--text-muted)] hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)]'
    }`;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listId}
        aria-label="Language"
        className={triggerClass}
        onClick={() => setOpen((v) => !v)}
      >
        <span>{current.label}</span>
        <IconChevronDown
          className={`h-4 w-4 shrink-0 text-[var(--text-muted)] transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open ? (
        <div
          id={listId}
          role="listbox"
          aria-label="Language"
          className="absolute right-0 top-[calc(100%+0.25rem)] z-50 min-w-full overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-glass)] py-0.5 shadow-lg backdrop-blur-sm"
        >
          {LOCALE_OPTIONS.map((opt) => (
            <button
              key={opt.code}
              type="button"
              role="option"
              aria-selected={locale === opt.code}
              className={itemClass(locale === opt.code)}
              onClick={() => {
                setLocale(opt.code);
                setOpen(false);
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** Locale, theme, and history with spacing only (hero nav and fixed corners). */
export function NavbarToolbar({ historySlot }: { historySlot: ReactNode }) {
  return (
    <div className="flex items-center gap-3 sm:gap-4">
      <LocaleSelector />
      <ThemeToggle />
      {historySlot}
    </div>
  );
}
