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
  toggle: () => void
  setEnabled: (v: boolean) => void
}

const BackgroundMotionContext = createContext<Ctx | null>(null)

function readStored(): boolean {
  if (globalThis.window === undefined) return true
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === "0") return false
    if (v === "1") return true
  } catch {
    // ignore
  }
  return true
}

export function BackgroundMotionProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [enabled, setEnabledState] = useState(true)

  useEffect(() => {
    setEnabledState(readStored())
  }, [])

  const setEnabled = useCallback((v: boolean) => {
    setEnabledState(v)
    if (globalThis.window === undefined) return
    try {
      localStorage.setItem(STORAGE_KEY, v ? "1" : "0")
    } catch {
      // ignore
    }
  }, [])

  const toggle = useCallback(() => setEnabled((v) => !v), [setEnabled])

  const value = useMemo<Ctx>(() => ({ enabled, toggle, setEnabled }), [enabled, toggle, setEnabled])

  return <BackgroundMotionContext.Provider value={value}>{children}</BackgroundMotionContext.Provider>
}

export function useBackgroundMotion() {
  const ctx = useContext(BackgroundMotionContext)
  if (!ctx) throw new Error("useBackgroundMotion must be used within BackgroundMotionProvider")
  return ctx
}

