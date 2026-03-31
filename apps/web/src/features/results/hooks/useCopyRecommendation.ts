import { useCallback, useRef, useState } from "react"

import type { ModelDecision } from "@/features/results/types"
import { formatScoreOutOfTen } from "@/features/results/utils/resultsView"

type CopyRecommendationState = {
  copied: boolean
  handleCopy: () => void
}

export function useCopyRecommendation(top: ModelDecision): CopyRecommendationState {
  const [copied, setCopied] = useState(false)
  const resetTimerRef = useRef<number | null>(null)

  const handleCopy = useCallback(() => {
    const why = top.why?.length ? `\nWhy:\n- ${top.why.join("\n- ")}` : ""
    const text = `Recommended: ${top.name} (${top.provider})\nScore: ${formatScoreOutOfTen(top.score)}${why}`

    navigator.clipboard.writeText(text).then(
      () => {
        setCopied(true)
        if (resetTimerRef.current) globalThis.clearTimeout(resetTimerRef.current)
        resetTimerRef.current = globalThis.setTimeout(() => setCopied(false), 2000)
      },
      () => {
        setCopied(false)
      },
    )
  }, [top])

  return {
    copied,
    handleCopy,
  }
}
