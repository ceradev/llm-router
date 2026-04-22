import type { Priority } from "@/features/landing/types"
import type {
  CategoryPick,
  DecisionMetricKey,
  ModelDecision,
  ResultsDecisionPayload,
  ResultsRoutingInfo,
} from "@/features/results/types"
import type { TranslationKey } from "@/i18n/translations"
import type { RankedModel } from "../utils"

export type ProvidersBanner = {
  tone: "warn" | "info"
  title: string
  body: string
}

export function formatScoreOutOfTen(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  const clamped = Math.max(1, Math.min(10, value))
  return clamped.toFixed(1)
}

export function truncateText(s: string, max: number): string {
  const t = s.trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

export function uniqueBenchmarkModels(models: ModelDecision[]): ModelDecision[] {
  const seen = new Set<string>()
  const out: ModelDecision[] = []
  for (const m of models) {
    if (seen.has(m.modelId)) continue
    seen.add(m.modelId)
    out.push(m)
  }
  return out
}

function metricsForPriority(priority: Priority) {
  if (priority === "quality") {
    return { reasoning: 92, speed: 70, costEfficiency: 62, contextWindow: 78 }
  }
  if (priority === "speed") {
    return { reasoning: 78, speed: 92, costEfficiency: 78, contextWindow: 70 }
  }
  return { reasoning: 84, speed: 82, costEfficiency: 92, contextWindow: 70 }
}

function deriveWhy(priority: Priority): string[] {
  if (priority === "quality") {
    return [
      "More reliable multi-step reasoning on complex prompts.",
      "Better instruction-following when requirements are ambiguous.",
      "Higher success rate on long, structured outputs.",
    ]
  }
  if (priority === "speed") {
    return [
      "Lower latency for interactive iteration loops.",
      "Good enough reasoning for everyday tasks without the wait.",
      "Predictable response time under typical load.",
    ]
  }
  return [
    "Best cost/quality balance for your prompt shape.",
    "Lower per-call spend while keeping outputs usable.",
    "More efficient for frequent or batch usage.",
  ]
}

function mockModelId(name: string): string {
  return `mock/${name.toLowerCase().replaceAll(/\s+/g, "-")}`
}

function toDecisionModel(
  m: RankedModel,
  id: string,
  priority: Priority,
): ModelDecision {
  return {
    id,
    modelId: mockModelId(m.name),
    name: m.name,
    provider: m.provider,
    score: Math.round((m.score / 10) * 10) / 10,
    latencyMs: m.latencyMs,
    cost: { rel: m.costRel },
    contextWindowTokens: 200_000,
    maxOutputTokens: 8192,
    modelTypeLabels: id === "top" ? ["chat", "json", "tools"] : ["chat", "json"],
    publicStatusKey: "verified",
    evaluationStatus: "verified",
    why: id === "top" ? deriveWhy(priority) : [],
    pros: [
      m.note,
      m.costRel === "low"
        ? "Lower relative cost for this priority."
        : "Strong overall performance.",
    ],
    cons: [
      m.costRel === "high"
        ? "Higher relative cost."
        : "Trade-offs depend on workload and context size.",
    ],
    metrics: metricsForPriority(priority),
    actions: undefined,
    rankingReasonKey:
      id === "top" ? "rankingReasonBestOverallBalanced" : undefined,
  }
}

export function buildFallbackPayload(
  priority: Priority,
  ranked: RankedModel[],
): ResultsDecisionPayload {
  const rankedTop = ranked[0]
  const rankedRunners = ranked.slice(1)

  const baseCategoryPicks: CategoryPick[] = rankedRunners.slice(0, 2).map((m, idx) => {
    const dm = toDecisionModel(m, `cat${idx}`, priority)
    const kinds: CategoryPick["kind"][] = ["quality", "cost", "speed"]
    const kind = kinds[idx] ?? "quality"
    const keys: Record<CategoryPick["kind"], TranslationKey> = {
      quality: "rankingReasonCategoryQuality",
      cost: "rankingReasonCategoryCost",
      speed: "rankingReasonCategorySpeed",
    }
    return {
      kind,
      model: dm,
      reasonKey: keys[kind],
      sameAsBest: false,
    }
  })
  const filler = rankedRunners[1] ?? rankedTop
  const categoryPicksFallback: CategoryPick[] =
    baseCategoryPicks.length >= 3
      ? baseCategoryPicks.slice(0, 3)
      : [
          ...baseCategoryPicks,
          {
            kind: "speed",
            model: toDecisionModel(filler, "cat-speed", priority),
            reasonKey: "rankingReasonCategorySpeed",
            sameAsBest: false,
          },
        ]

  return {
    topPick: toDecisionModel(rankedTop, "top", priority),
    freeAlternative: {
      id: "free",
      modelId: mockModelId("Llama 3"),
      name: "Llama 3",
      provider: "Open source",
      score: Math.max(1, Math.round(((rankedTop.score / 10) - 2) * 10) / 10),
      latencyMs: undefined,
      cost: { rel: "low" },
      contextWindowTokens: 128_000,
      maxOutputTokens: 8192,
      why: [],
      pros: ["No usage cost.", "Runs locally or via free-tier APIs."],
      cons: ["Lower accuracy on hard tasks.", "Can be slower depending on hardware."],
      metrics: { reasoning: 70, speed: 55, costEfficiency: 95, contextWindow: 60 },
      actions: [
        { kind: "runLocal", label: "Run locally" },
        { kind: "useFreeApi", label: "Use free API" },
      ],
      rankingReasonKey: "rankingReasonFreeAlternative",
    },
    categoryPicks: categoryPicksFallback,
    extraAlternatives: rankedRunners.slice(0, 2).map((m, idx) =>
      toDecisionModel(m, `extra${idx + 1}`, priority),
    ),
    isMock: true,
  }
}

export function buildProvidersBanner(
  routing: ResultsRoutingInfo | undefined,
): ProvidersBanner | null {
  if (!routing) return null
  if (!routing.preferredProvidersFallbackUsed) return null

  const names = routing.preferredProviders.length ? routing.preferredProviders.join(", ") : ""

  if (routing.preferredProvidersFallbackUsed) {
    return {
      tone: "warn",
      title: "Preferred providers unavailable.",
      body: names
        ? `No eligible models found for: ${names}. Showing all providers instead.`
        : "No eligible models found for preferred providers. Showing all providers instead.",
    }
  }
}

export function buildBenchmarkModels(payload: ResultsDecisionPayload): ModelDecision[] {
  const models = uniqueBenchmarkModels([
    payload.topPick,
    ...(payload.freeAlternative ? [payload.freeAlternative] : []),
    ...payload.categoryPicks.map((c) => c.model),
  ])

  return rebalanceBenchmarkMetrics(models)
}

function clamp01to100(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, value))
}

function spreadMetricForComparison(
  models: ModelDecision[],
  key: Extract<DecisionMetricKey, "reasoning" | "speed" | "costEfficiency">,
): ModelDecision[] {
  const values = models.map((m) => clamp01to100(m.metrics?.[key] ?? 0))
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min

  return models.map((model, idx) => {
    const value = values[idx]
    let normalized: number
    if (range <= 0.01) {
      // Avoid "all 100" rows that look fake when backend scores are tied.
      normalized = 70
    } else if (range < 5) {
      normalized = 60 + ((value - min) / range) * 20
    } else {
      normalized = 25 + ((value - min) / range) * 70
    }

    return {
      ...model,
      metrics: {
        ...model.metrics,
        [key]: clamp01to100(Math.round(normalized)),
      },
    }
  })
}

function rebalanceBenchmarkMetrics(models: ModelDecision[]): ModelDecision[] {
  let adjusted = [...models]
  adjusted = spreadMetricForComparison(adjusted, "reasoning")
  adjusted = spreadMetricForComparison(adjusted, "speed")
  adjusted = spreadMetricForComparison(adjusted, "costEfficiency")
  return adjusted
}
