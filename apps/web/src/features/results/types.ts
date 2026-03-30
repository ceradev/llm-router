export type DecisionMetricKey =
  | "reasoning"
  | "speed"
  | "costEfficiency"
  | "contextWindow"

export type DecisionMetrics = Record<DecisionMetricKey, number>

export type ModelCost = {
  rel: "low" | "medium" | "high"
  note?: string
}

export type ModelActionKind = "runLocal" | "useFreeApi" | "openProvider"

export type ModelAction = {
  kind: ModelActionKind
  label: string
  href?: string
}

export type ModelDecision = {
  id: string
  /** API routing key, e.g. openrouter/anthropic/claude-3-5-sonnet */
  modelId: string
  name: string
  provider: string
  score: number
  /** Observed latency for this request, only when this model was executed */
  latencyMs?: number
  cost?: ModelCost
  contextWindowTokens?: number
  maxOutputTokens?: number | null
  why: string[]
  pros: string[]
  cons: string[]
  metrics: DecisionMetrics
  actions?: ModelAction[]
  /** i18n key from backend ranking summary */
  rankingReasonKey?: string
  sameAsBestOverall?: boolean
  /** Scoring / routing detail from backend ranking row */
  rankingExplanation?: string
  modelCategories?: string[]
  technicalCapabilities?: string[]
  verificationScopes?: string[]
  /** Legacy categories kept while backend migrates clients. */
  capabilities?: string[]
  supportsJson?: boolean
  supportsTools?: boolean
  /** From catalog tier (e.g. OpenRouter sync), not inferred from name */
  isFreeTier?: boolean
  tier?: string
  evaluationStatus?: string
  supportsVision?: boolean
  inputModalities?: string[]
  outputModalities?: string[]
  /** Derived on the server (e.g. chat, vision, json) */
  modelTypeLabels?: string[]
  isVerified?: boolean
  /** Maps to product status badge; omitted for rejected */
  publicStatusKey?: string | null
}

export type CategoryPick = {
  kind: "quality" | "cost" | "speed"
  model: ModelDecision
  reasonKey: string
  sameAsBest: boolean
}

export type RoutingAttempt = {
  provider: string
  modelId: string
  status: string
  detail: string
  latencyMs: number | null
}

/** Extra transparency from the gateway response (omitted for offline mock data). */
export type ResultsRoutingInfo = {
  intent: string
  priority: string
  explanation: string
  routingReason: string
  fallbackUsed: boolean
  recommendedModelId: string
  executedModelId: string
  executedProvider: string
  responseLatencyMs: number | null
  attempts: RoutingAttempt[]
  candidateModels: string[]
  preferredProviders: string[]
  preferredProvidersApplied: boolean
  preferredProvidersFallbackUsed: boolean
}

export type ResultsDecisionPayload = {
  topPick: ModelDecision
  freeAlternative: ModelDecision | null
  categoryPicks: CategoryPick[]
  extraAlternatives: ModelDecision[]
  routing?: ResultsRoutingInfo
  /** True when UI is rendering offline/mock fallback, not backend ranking. */
  isMock?: boolean
}

