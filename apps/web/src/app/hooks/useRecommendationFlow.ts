import { useCallback, useEffect, useRef, useState } from "react"

import type {
  Priority,
  ResponseDepth,
  UseCaseId,
} from "@/features/landing/types/routingOptions"
import { getHistoryResult, saveHistoryResult } from "@/features/history/utils/historyResultsCache"
import type { ResultsDecisionPayload } from "@/features/results"
import { fetchRecommendation } from "@/shared/api/recommend"

type StartResultsFetchArgs = {
  prompt: string
  priority: Priority
  useCases: Set<UseCaseId>
  providers: Set<string>
  responseDepth: ResponseDepth
}

type RecommendationFlow = {
  results: ResultsDecisionPayload | null
  startResultsFetch: (args: StartResultsFetchArgs) => void
  restoreResultsFromHistory: (requestId: string) => boolean
  abortInFlight: () => void
}

export function useRecommendationFlow(): RecommendationFlow {
  const [results, setResults] = useState<ResultsDecisionPayload | null>(null)
  const resultsAbortRef = useRef<AbortController | null>(null)

  const abortInFlight = useCallback(() => {
    resultsAbortRef.current?.abort()
  }, [])

  const restoreResultsFromHistory = useCallback((requestId: string) => {
    const cached = getHistoryResult(requestId)
    if (!cached) return false
    setResults(cached)
    return true
  }, [])

  const startResultsFetch = useCallback(
    ({
      prompt,
      priority,
      useCases,
      providers,
      responseDepth,
    }: StartResultsFetchArgs) => {
      abortInFlight()
      const controller = new AbortController()
      resultsAbortRef.current = controller

      setResults(null)

      fetchRecommendation(
        {
          prompt,
          priority,
          useCases: Array.from(useCases),
          preferredProviders: Array.from(providers),
          responseDepth,
        },
        { signal: controller.signal },
      ).then(
        (payload) => {
          if (controller.signal.aborted) return
          setResults(payload)
          saveHistoryResult(payload)
        },
        () => {
          if (controller.signal.aborted) return
          setResults(null)
        },
      )
    },
    [abortInFlight],
  )

  useEffect(() => abortInFlight, [abortInFlight])

  return {
    results,
    startResultsFetch,
    restoreResultsFromHistory,
    abortInFlight,
  }
}
