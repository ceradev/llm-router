import { getSessionId } from "./session"

const API_BASE = import.meta.env.PUBLIC_API_BASE_URL as string

type PriorityMapping = Record<string, string>

const PRIORITY_MAP: PriorityMapping = {
  quality: "high_quality",
  speed: "low_latency",
  cost: "low_cost",
}

export type RankingHighlightBackend = {
  model_id: string
  display_name: string
  provider: string
  reason_key: string
  same_as_best_overall: boolean
}

export type RankingSummaryBackend = {
  best_overall: RankingHighlightBackend
  free_alternative: RankingHighlightBackend | null
  best_quality: RankingHighlightBackend
  best_cost: RankingHighlightBackend
  best_speed: RankingHighlightBackend
}

export type GatewayBackendResponse = {
  request_id: string
  content: string
  provider: string
  model_id: string
  recommended_model_id: string
  response_latency_ms: number | null
  intent: string
  priority: string
  routing_reason: string
  explanation: string
  ranking_summary: RankingSummaryBackend
  ranking: Array<{
    model_id: string
    rank: number
    quality_score: number
    latency_score: number
    cost_score: number
    final_score: number
    explanation: string
    pros: string[] | null
    cons: string[] | null
    context_window: number | null
    max_output_tokens: number | null
    supports_json: boolean
    supports_tools: boolean
    capabilities: string[]
    is_free: boolean
    tier: string
  }>
  fallback_used: boolean
  candidate_models: string[]
  attempts: Array<{
    provider: string
    model_id: string
    status: string
    detail: string
    latency_ms: number | null
  }>
}

export async function callGateway(
  prompt: string,
  priority: string,
  signal?: AbortSignal,
): Promise<GatewayBackendResponse> {
  const res = await fetch(`${API_BASE}/v1/chat/completions/advanced`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": getSessionId(),
    },
    body: JSON.stringify({
      prompt,
      priority: PRIORITY_MAP[priority] ?? "balanced",
      max_tokens: null,
    }),
    signal,
  })
  if (!res.ok) throw new Error(`Gateway ${res.status}`)
  return res.json() as Promise<GatewayBackendResponse>
}
