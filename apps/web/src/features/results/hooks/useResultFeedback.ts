import { useCallback, useMemo, useState } from "react"

import type { ModelDecision, ResultsRoutingInfo } from "@/features/results/types"
import {
  submitModelFeedback,
  submitRequestFeedback,
} from "@/shared/api/modelFeedback"

export type FeedbackState = "idle" | "submitting" | "success" | "error"

type ResultFeedbackState = {
  canSendFeedback: boolean
  feedbackRating: number | null
  feedbackState: FeedbackState
  handleRating: (rating: number) => void
}

type UseResultFeedbackArgs = {
  isMock?: boolean
  routing?: ResultsRoutingInfo
  top: ModelDecision
}

export function useResultFeedback({
  isMock,
  routing,
  top,
}: Readonly<UseResultFeedbackArgs>): ResultFeedbackState {
  const [feedbackRating, setFeedbackRating] = useState<number | null>(null)
  const [feedbackState, setFeedbackState] = useState<FeedbackState>("idle")

  const canSendFeedback = useMemo(
    () => !isMock && Boolean(top.modelId),
    [isMock, top.modelId],
  )

  const handleRating = useCallback(
    (rating: number) => {
      if (feedbackState === "submitting") return

      setFeedbackRating(rating)
      if (!canSendFeedback) {
        setFeedbackState("idle")
        return
      }

      setFeedbackState("submitting")
      const request = routing?.requestId
        ? submitRequestFeedback({
            requestId: routing.requestId,
            rating,
          })
        : submitModelFeedback({
            modelId: top.modelId,
            rating,
          })

      request.then(
        () => {
          setFeedbackState("success")
        },
        () => {
          setFeedbackState("error")
        },
      )
    },
    [canSendFeedback, feedbackState, routing?.requestId, top.modelId],
  )

  return {
    canSendFeedback,
    feedbackRating,
    feedbackState,
    handleRating,
  }
}
