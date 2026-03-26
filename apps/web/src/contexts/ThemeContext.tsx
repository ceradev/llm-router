import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'llm-router-theme';

type ContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ContextValue | null>(null);

function readSystemTheme(): Theme {
  if (globalThis.window === undefined) return 'dark';
  return globalThis.window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function readStored(): Theme {
  if (globalThis.window === undefined) return 'dark';
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
  return stored === 'light' || stored === 'dark' ? stored : readSystemTheme();
}

export function ThemeProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [themeState, setThemeState] = useState<Theme>(() => readStored());

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.classList.toggle('dark', next === 'dark');
    document.documentElement.classList.toggle('light', next === 'light');
    document.documentElement.dataset.theme = next;
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(themeState === 'dark' ? 'light' : 'dark');
  }, [themeState, setTheme]);

  useEffect(() => {
    setTheme(themeState);
  }, []);

  const value = useMemo(
    () => ({ theme: themeState, setTheme, toggleTheme }),
    [themeState, setTheme, toggleTheme],
  );

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
