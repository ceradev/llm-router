import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"

const STORAGE_KEY = "llm-router-bg-motion"

type Ctx = {
  enabled: boolean
  hasExplicitPreference: boolean
  toggle: () => void
  setEnabled: (v: boolean) => void
}

const BackgroundMotionContext = createContext<Ctx | null>(null)

function readStored(): { enabled: boolean; hasExplicitPreference: boolean } {
  if (globalThis.window === undefined) {
    return { enabled: true, hasExplicitPreference: false }
  }
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === "0") return { enabled: false, hasExplicitPreference: true }
    if (v === "1") return { enabled: true, hasExplicitPreference: true }
  } catch {
    // ignore
  }
  return { enabled: true, hasExplicitPreference: false }
}

export function BackgroundMotionProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [enabled, setEnabledState] = useState(true)
  const [hasExplicitPreference, setHasExplicitPreference] = useState(false)

  useEffect(() => {
    const stored = readStored()
    setEnabledState(stored.enabled)
    setHasExplicitPreference(stored.hasExplicitPreference)
  }, [])

  const setEnabled = useCallback((v: boolean) => {
    setEnabledState(v)
    setHasExplicitPreference(true)
    if (globalThis.window === undefined) return
    try {
      localStorage.setItem(STORAGE_KEY, v ? "1" : "0")
    } catch {
      // ignore
    }
  }, [])

  const toggle = useCallback(() => setEnabled(!enabled), [enabled, setEnabled])

  const value = useMemo<Ctx>(
    () => ({ enabled, hasExplicitPreference, toggle, setEnabled }),
    [enabled, hasExplicitPreference, toggle, setEnabled]
  )

  return <BackgroundMotionContext.Provider value={value}>{children}</BackgroundMotionContext.Provider>
}

export function useBackgroundMotion() {
  const ctx = useContext(BackgroundMotionContext)
  if (!ctx) throw new Error("useBackgroundMotion must be used within BackgroundMotionProvider")
  return ctx
}

