import type { GatewayBackendResponse, RankingHighlightBackend } from "./gateway"
import type {
  CategoryPick,
  ModelDecision,
  ResultsDecisionPayload,
  ResultsRoutingInfo,
} from "@/features/results/types"

function formatModelName(modelId: string): string {
  const name = modelId.split("/").pop() ?? modelId
  return name
    .replaceAll("-", " ")
    .split(" ")
    .map((part) => (part ? part[0].toUpperCase() + part.slice(1) : part))
    .join(" ")
}

function formatProvider(modelId: string): string {
  const slug = modelId.split("/").slice(0, -1).pop() ?? "unknown"
  const map: Record<string, string> = {
    openai: "OpenAI",
    anthropic: "Anthropic",
    "meta-llama": "Meta Llama",
    mistralai: "Mistral",
    deepseek: "DeepSeek",
    google: "Google",
  }
  return map[slug] ?? slug.charAt(0).toUpperCase() + slug.slice(1)
}

function scoreToPercent(score: number): number {
  return Math.round((score / 5) * 100)
}

/** Map catalog context size to chart bar 0–100 when we have token counts. */
function contextTokensToChartScore(tokens: number | null | undefined): number {
  if (tokens == null || !Number.isFinite(tokens) || tokens <= 0) return 50
  const log = Math.log10(tokens)
  const raw = 18 + (log - 2.5) * 28
  return Math.max(8, Math.min(100, Math.round(raw)))
}

function findRankRow(
  ranking: GatewayBackendResponse["ranking"],
  modelId: string,
): GatewayBackendResponse["ranking"][0] | undefined {
  return ranking.find((r) => r.model_id === modelId)
}

function toModelDecision(
  rankItem: GatewayBackendResponse["ranking"][0],
  id: string,
  options: {
    why: string[]
    isTop: boolean
    rankingReasonKey?: string
    sameAsBestOverall?: boolean
    measuredLatencyMs?: number | null
  },
): ModelDecision {
  const ctx = rankItem.context_window ?? undefined
  const maxOut = rankItem.max_output_tokens ?? null
  const caps = rankItem.capabilities ?? []
  let costRel: "low" | "medium" | "high" = "high"
  if (rankItem.cost_score >= 4) {
    costRel = "low"
  } else if (rankItem.cost_score >= 3) {
    costRel = "medium"
  }
  const whyRouting = options.isTop ? options.why : []
  return {
    id,
    modelId: rankItem.model_id,
    name: formatModelName(rankItem.model_id),
    provider: formatProvider(rankItem.model_id),
    score: scoreToPercent(rankItem.final_score),
    latencyMs:
      options.measuredLatencyMs != null && options.measuredLatencyMs >= 0
        ? options.measuredLatencyMs
        : undefined,
    cost: { rel: costRel },
    contextWindowTokens: ctx,
    maxOutputTokens: maxOut,
    why: whyRouting,
    pros: rankItem.pros ?? [],
    cons: rankItem.cons ?? [],
    metrics: {
      reasoning: scoreToPercent(rankItem.quality_score),
      speed: scoreToPercent(rankItem.latency_score),
      costEfficiency: scoreToPercent(rankItem.cost_score),
      contextWindow: contextTokensToChartScore(ctx),
    },
    actions: undefined,
    rankingReasonKey: options.rankingReasonKey,
    sameAsBestOverall: options.sameAsBestOverall,
    rankingExplanation: rankItem.explanation,
    modelCategories: rankItem.model_categories ?? [],
    technicalCapabilities: rankItem.technical_capabilities ?? [],
    verificationScopes: rankItem.verification_scopes ?? [],
    capabilities: caps,
    supportsJson: rankItem.supports_json,
    supportsTools: rankItem.supports_tools,
    isFreeTier: rankItem.is_free,
    tier: rankItem.tier,
    evaluationStatus: rankItem.evaluation_status ?? "cataloged",
    supportsVision: rankItem.supports_vision ?? false,
    inputModalities: rankItem.input_modalities ?? [],
    outputModalities: rankItem.output_modalities ?? [],
    modelTypeLabels: rankItem.model_type_labels ?? [],
    isVerified: rankItem.is_verified ?? false,
    publicStatusKey: rankItem.public_status_key ?? null,
  }
}

function decisionFromHighlight(
  data: GatewayBackendResponse,
  highlight: RankingHighlightBackend,
  id: string,
  why: string[],
  isTop: boolean,
): ModelDecision {
  const measured =
    highlight.model_id === data.model_id ? data.response_latency_ms : undefined
  const row = findRankRow(data.ranking, highlight.model_id)
  if (row) {
    return toModelDecision(row, id, {
      why,
      isTop,
      rankingReasonKey: highlight.reason_key,
      sameAsBestOverall: highlight.same_as_best_overall,
      measuredLatencyMs: measured,
    })
  }
  return {
    id,
    modelId: highlight.model_id,
    name: highlight.display_name,
    provider: highlight.provider,
    score: 0,
    latencyMs:
      measured != null && measured >= 0 ? measured : undefined,
    cost: { rel: "medium" },
    contextWindowTokens: undefined,
    maxOutputTokens: null,
    why: isTop ? why : [],
    pros: [],
    cons: [],
    metrics: {
      reasoning: 50,
      speed: 50,
      costEfficiency: 50,
      contextWindow: 50,
    },
    rankingReasonKey: highlight.reason_key,
    sameAsBestOverall: highlight.same_as_best_overall,
  }
}

function featuredModelIds(summary: GatewayBackendResponse["ranking_summary"]): Set<string> {
  const ids = new Set<string>()
  ids.add(summary.best_overall.model_id)
  if (summary.free_alternative?.model_id) {
    ids.add(summary.free_alternative.model_id)
  }
  ids.add(summary.best_quality.model_id)
  ids.add(summary.best_cost.model_id)
  ids.add(summary.best_speed.model_id)
  return ids
}

function buildRoutingInfo(data: GatewayBackendResponse): ResultsRoutingInfo {
  return {
    intent: data.intent,
    priority: data.priority,
    explanation: data.explanation,
    routingReason: data.routing_reason,
    fallbackUsed: data.fallback_used,
    recommendedModelId: data.recommended_model_id,
    executedModelId: data.model_id,
    executedProvider: data.provider,
    responseLatencyMs: data.response_latency_ms,
    attempts: data.attempts.map((a) => ({
      provider: a.provider,
      modelId: a.model_id,
      status: a.status,
      detail: a.detail,
      latencyMs: a.latency_ms,
    })),
    candidateModels: data.candidate_models,
    preferredProviders: data.preferred_providers ?? [],
    preferredProvidersApplied: Boolean(data.preferred_providers_applied),
    preferredProvidersFallbackUsed: Boolean(data.preferred_providers_fallback_used),
  }
}

export function gatewayResponseToResultsPayload(
  data: GatewayBackendResponse,
): ResultsDecisionPayload {
  const sorted = [...data.ranking].sort((a, b) => a.rank - b.rank)
  if (!sorted.length) {
    throw new Error("empty_ranking")
  }

  const summary = data.ranking_summary
  let whyRouting: string[] = []
  if (data.explanation) {
    whyRouting = [data.explanation]
  } else if (data.routing_reason) {
    whyRouting = [data.routing_reason]
  }

  const topPick = decisionFromHighlight(data, summary.best_overall, "top", whyRouting, true)

  const freeAlternative: ModelDecision | null = summary.free_alternative
    ? decisionFromHighlight(data, summary.free_alternative, "free", [], false)
    : null

  const categorySpecs: Array<{
    kind: CategoryPick["kind"]
    highlight: RankingHighlightBackend
  }> = [
    { kind: "quality", highlight: summary.best_quality },
    { kind: "cost", highlight: summary.best_cost },
    { kind: "speed", highlight: summary.best_speed },
  ]

  const categoryPicks: CategoryPick[] = categorySpecs.map(({ kind, highlight }) => ({
    kind,
    model: decisionFromHighlight(data, highlight, `cat-${kind}`, [], false),
    reasonKey: highlight.reason_key,
    sameAsBest: highlight.same_as_best_overall,
  }))

  const featured = featuredModelIds(summary)
  const extraAlternatives = sorted
    .filter((r) => !featured.has(r.model_id))
    .slice(0, 4)
    .map((r, i) =>
      toModelDecision(r, `extra${i + 1}`, { why: [], isTop: false }),
    )

  return {
    topPick,
    freeAlternative,
    categoryPicks,
    extraAlternatives,
    routing: buildRoutingInfo(data),
  }
}
