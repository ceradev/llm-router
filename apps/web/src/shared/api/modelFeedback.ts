import { getSessionId } from "./session"

const API_BASE = import.meta.env.PUBLIC_API_BASE_URL as string

export type SubmitModelFeedbackPayload = {
  modelId: string
  rating: number
  comment?: string
  requestId?: string
}

export async function submitModelFeedback(payload: SubmitModelFeedbackPayload): Promise<void> {
  const res = await fetch(`${API_BASE}/v1/models/${encodeURIComponent(payload.modelId)}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": getSessionId(),
    },
    body: JSON.stringify({
      rating: payload.rating,
      comment: payload.comment ?? null,
      request_id: payload.requestId ?? null,
    }),
  })
  if (!res.ok) throw new Error(`Model feedback ${res.status}`)
}

export async function submitRequestFeedback(payload: {
  requestId: string
  rating: number
  comment?: string
}): Promise<void> {
  const res = await fetch(`${API_BASE}/v1/requests/${encodeURIComponent(payload.requestId)}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": getSessionId(),
    },
    body: JSON.stringify({
      rating: payload.rating,
      comment: payload.comment ?? null,
    }),
  })
  if (!res.ok) throw new Error(`Request feedback ${res.status}`)
}
