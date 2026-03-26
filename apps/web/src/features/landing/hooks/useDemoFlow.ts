import { useEffect, useMemo, useState } from "react"

export type DemoPhase = "input" | "loading" | "result"

const PHASES: readonly DemoPhase[] = ["input", "loading", "result"] as const

const DEFAULT_TIMINGS_MS: Record<DemoPhase, number> = {
  input: 500,
  loading: 1200,
  result: 2000,
}

type UseDemoFlowOptions = {
  enabled?: boolean
  initialPhase?: DemoPhase
  timingsMs?: Partial<Record<DemoPhase, number>>
}

export function useDemoFlow(options?: UseDemoFlowOptions) {
  const { enabled = true, initialPhase = "input", timingsMs } = options ?? {}
  const [phase, setPhase] = useState<DemoPhase>(initialPhase)

  const resolvedTimingsMs = useMemo(() => {
    if (!timingsMs) return DEFAULT_TIMINGS_MS
    return { ...DEFAULT_TIMINGS_MS, ...timingsMs }
  }, [timingsMs])

  useEffect(() => {
    if (!enabled) return

    const idx = PHASES.indexOf(phase)
    const nextPhase = PHASES[(idx + 1) % PHASES.length]
    const duration = resolvedTimingsMs[phase]

    const timerId = globalThis.setTimeout(() => {
      setPhase(nextPhase)
    }, duration)

    return () => globalThis.clearTimeout(timerId)
  }, [enabled, phase, resolvedTimingsMs])

  return { phase }
}

