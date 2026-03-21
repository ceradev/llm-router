import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
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
  if (typeof window === 'undefined') return 'en';
  const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
  return stored === 'es' || stored === 'en' ? stored : 'en';
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => readStored());

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    localStorage.setItem(STORAGE_KEY, next);
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

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within I18nProvider');
  return ctx;
}
