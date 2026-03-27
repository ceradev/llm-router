import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Locale, TranslationKey } from '../i18n/translations';
import { translations } from '../i18n/translations';

const STORAGE_KEY = 'llm-router-locale';

type ContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey) => string;
};

const I18nContext = createContext<ContextValue | null>(null);

function readStored(): Locale {
  if (globalThis.window === undefined) return 'en';
  const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
  return stored === 'es' || stored === 'en' ? stored : 'en';
}

export function I18nProvider({ children }: Readonly<{ children: ReactNode }>) {
  // Keep the server + first client render deterministic to avoid React hydration mismatches.
  // We then reconcile with localStorage after mount.
  const [locale, setLocaleState] = useState<Locale>('en');

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    if (globalThis.window === undefined) return;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore storage failures (private mode, blocked, etc.)
    }
  }, []);

  const t = useCallback(
    (key: TranslationKey) => {
      return translations[locale][key] ?? translations.en[key] ?? key;
    },
    [locale],
  );

  useEffect(() => {
    document.documentElement.lang = locale === 'es' ? 'es' : 'en';
  }, [locale]);

  useEffect(() => {
    const stored = readStored();
    setLocaleState((prev) => (prev === stored ? prev : stored));
  }, []);

  const value = useMemo<ContextValue>(() => ({ locale, setLocale, t }), [locale, setLocale, t]);

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within I18nProvider');
  return ctx;
}
