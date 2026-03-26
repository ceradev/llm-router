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
  name: string
  provider: string
  score: number
  latencyMs?: number
  cost?: ModelCost
  contextWindowTokens?: number
  why: string[]
  pros: string[]
  cons: string[]
  metrics: DecisionMetrics
  actions?: ModelAction[]
}

export type ResultsDecisionPayload = {
  topPick: ModelDecision
  freeAlternative: ModelDecision
  alternatives: ModelDecision[]
}

