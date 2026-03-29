import type { Priority } from "@/features/landing/types/routingOptions"
import type {
  CategoryPick,
  DecisionMetrics,
  ModelDecision,
  ResultsDecisionPayload,
} from "@/features/results/types"
import { callGateway } from "./gateway"
import { gatewayResponseToResultsPayload } from "./converters"

export type RecommendRequest = { prompt: string; priority?: Priority }

function clamp01to100(n: number) {
  if (!Number.isFinite(n)) return 0
  return Math.max(0, Math.min(100, Math.round(n)))
}

function normalizeMetrics(metrics: Partial<DecisionMetrics>): DecisionMetrics {
  return {
    reasoning: clamp01to100(metrics.reasoning ?? 0),
    speed: clamp01to100(metrics.speed ?? 0),
    costEfficiency: clamp01to100(metrics.costEfficiency ?? 0),
    contextWindow: clamp01to100(metrics.contextWindow ?? 0),
  }
}

function coerceCategoryPick(c: CategoryPick): CategoryPick {
  return {
    ...c,
    model: coerceModelDecision(c.model),
  }
}

function coerceModelDecision(m: ModelDecision): ModelDecision {
  return {
    ...m,
    modelId: m.modelId || m.id,
    why: Array.isArray(m.why) ? m.why : [],
    pros: Array.isArray(m.pros) ? m.pros : [],
    cons: Array.isArray(m.cons) ? m.cons : [],
    metrics: normalizeMetrics(m.metrics ?? ({} as Partial<DecisionMetrics>)),
  }
}

function mockDecisionPayload(_prompt: string, priority: Priority): ResultsDecisionPayload {
  let base: {
    top: { name: string; provider: string; modelId: string }
    alt1: { name: string; provider: string; modelId: string }
    alt2: { name: string; provider: string; modelId: string }
  }

  if (priority === "quality") {
    base = {
      top: { name: "Claude 3.5 Sonnet", provider: "Anthropic", modelId: "anthropic/claude-3-5-sonnet" },
      alt1: { name: "GPT-4o", provider: "OpenAI", modelId: "openai/gpt-4o" },
      alt2: { name: "Gemini 1.5 Pro", provider: "Google", modelId: "google/gemini-1.5-pro" },
    }
  } else if (priority === "speed") {
    base = {
      top: { name: "GPT-4o mini", provider: "OpenAI", modelId: "openai/gpt-4o-mini" },
      alt1: { name: "Claude 3 Haiku", provider: "Anthropic", modelId: "anthropic/claude-3-haiku" },
      alt2: { name: "Gemini 1.5 Flash", provider: "Google", modelId: "google/gemini-1.5-flash" },
    }
  } else {
    base = {
      top: { name: "Claude 3 Haiku", provider: "Anthropic", modelId: "anthropic/claude-3-haiku" },
      alt1: { name: "GPT-4o mini", provider: "OpenAI", modelId: "openai/gpt-4o-mini" },
      alt2: { name: "Gemini 1.5 Flash", provider: "Google", modelId: "google/gemini-1.5-flash" },
    }
  }

  const mk = (
    id: string,
    n: string,
    p: string,
    modelId: string,
    score: number,
    ctx: number,
    maxOut: number,
  ): ModelDecision => {
    const why =
      id === "top"
        ? [
            "Consistently strong reasoning on multi-step tasks.",
            "More reliable instruction-following for ambiguous prompts.",
            "Balanced trade‑offs for your selected priority.",
          ]
        : []

    const pros =
      id === "free"
        ? ["No usage cost.", "Runs locally or via free-tier APIs."]
        : ["Strong overall performance.", "Widely supported tooling."]

    const cons =
      id === "free"
        ? ["Lower accuracy on hard tasks.", "Can be slower depending on hardware."]
        : ["May cost more at scale.", "Trade‑offs depend on your workload."]

    let metrics: Partial<DecisionMetrics>
    if (id === "top") {
      metrics = { reasoning: 92, speed: 70, costEfficiency: 62, contextWindow: 78 }
    } else if (id === "alt1" || id === "cat-quality") {
      metrics = { reasoning: 90, speed: 72, costEfficiency: 58, contextWindow: 72 }
    } else if (id === "alt2" || id === "cat-cost") {
      metrics = { reasoning: 78, speed: 80, costEfficiency: 94, contextWindow: 65 }
    } else if (id === "cat-speed") {
      metrics = { reasoning: 76, speed: 94, costEfficiency: 72, contextWindow: 62 }
    } else {
      metrics = { reasoning: 70, speed: 55, costEfficiency: 95, contextWindow: 60 }
    }

    const actions =
      id === "free"
        ? [
            { kind: "runLocal" as const, label: "Run locally" as const },
            { kind: "useFreeApi" as const, label: "Use free API" as const },
          ]
        : undefined

    return {
      id,
      modelId,
      name: n,
      provider: p,
      score,
      latencyMs: undefined,
      cost: undefined,
      contextWindowTokens: ctx,
      maxOutputTokens: maxOut,
      why,
      pros,
      cons,
      metrics: normalizeMetrics(metrics),
      actions,
    }
  }

  const top = mk("top", base.top.name, base.top.provider, base.top.modelId, 96, 200_000, 8192)
  top.rankingReasonKey = "rankingReasonBestOverallBalanced"

  const free = mk("free", "Llama 3", "Open source", "meta-llama/llama-3", 74, 128_000, 8192)

  const categoryPicks: CategoryPick[] = [
    {
      kind: "quality",
      model: mk("cat-quality", base.alt1.name, base.alt1.provider, base.alt1.modelId, 92, 128_000, 4096),
      reasonKey: "rankingReasonCategoryQuality",
      sameAsBest: false,
    },
    {
      kind: "cost",
      model: mk("cat-cost", base.alt2.name, base.alt2.provider, base.alt2.modelId, 88, 1_000_000, 8192),
      reasonKey: "rankingReasonCategoryCost",
      sameAsBest: false,
    },
    {
      kind: "speed",
      model: mk("cat-speed", "Gemini 1.5 Flash", "Google", "google/gemini-1.5-flash", 85, 1_000_000, 8192),
      reasonKey: "rankingReasonCategorySpeed",
      sameAsBest: false,
    },
  ]

  const extraAlternatives = [
    mk("extra1", base.alt1.name, base.alt1.provider, base.alt1.modelId, 90, 128_000, 4096),
    mk("extra2", base.alt2.name, base.alt2.provider, base.alt2.modelId, 88, 256_000, 8192),
  ]

  return {
    topPick: top,
    freeAlternative: free,
    categoryPicks,
    extraAlternatives,
  }
}

function priorityForGateway(req: RecommendRequest): string {
  return req.priority ?? "balanced"
}

function priorityForMock(req: RecommendRequest): Priority {
  return req.priority ?? "quality"
}

export async function fetchRecommendation(
  req: RecommendRequest,
  opts?: { signal?: AbortSignal },
): Promise<ResultsDecisionPayload> {
  const controller = new AbortController()
  const signal = opts?.signal
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener("abort", () => controller.abort(), { once: true })
  }

  try {
    const data = await callGateway(req.prompt, priorityForGateway(req), controller.signal)
    const payload = gatewayResponseToResultsPayload(data)
    return {
      topPick: coerceModelDecision(payload.topPick),
      freeAlternative: payload.freeAlternative
        ? coerceModelDecision(payload.freeAlternative)
        : null,
      categoryPicks: payload.categoryPicks.map(coerceCategoryPick),
      extraAlternatives: payload.extraAlternatives.map(coerceModelDecision),
      routing: payload.routing,
    }
  } catch (e) {
    if (controller.signal.aborted) throw e
    return mockDecisionPayload(req.prompt, priorityForMock(req))
  }
}
