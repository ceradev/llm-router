import { useEffect, useMemo, useState } from "react"

import { ANALYZING_STEP_KEYS } from "../config"

export function useAnalyzingProgress({
  reduceMotion,
  onComplete,
}: Readonly<{
  reduceMotion: boolean
  onComplete: () => void
}>) {
  const [phaseIndex, setPhaseIndex] = useState(0)

  useEffect(() => {
    if (phaseIndex >= ANALYZING_STEP_KEYS.length) {
      const id = setTimeout(onComplete, 1200)
      return () => clearTimeout(id)
    }

    const delay = reduceMotion ? 400 : 1100
    const id = setTimeout(() => setPhaseIndex((n) => n + 1), delay)
    return () => clearTimeout(id)
  }, [phaseIndex, onComplete, reduceMotion])

  const activeStepIndex = Math.min(phaseIndex, ANALYZING_STEP_KEYS.length - 1)

  const steps = useMemo(
    () => ANALYZING_STEP_KEYS.map((key) => ({ key })),
    []
  )

  return { steps, activeStepIndex }
}

