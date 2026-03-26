import type { Priority } from "@/features/hero"
import type {
  DecisionMetrics,
  ModelDecision,
  ResultsDecisionPayload,
} from "@/features/results/types"

type RecommendRequest = {
  prompt: string
  priority: Priority
}

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

function coerceModelDecision(m: ModelDecision): ModelDecision {
  return {
    ...m,
    why: Array.isArray(m.why) ? m.why : [],
    pros: Array.isArray(m.pros) ? m.pros : [],
    cons: Array.isArray(m.cons) ? m.cons : [],
    metrics: normalizeMetrics(m.metrics ?? ({} as Partial<DecisionMetrics>)),
  }
}

function mockDecisionPayload(priority: Priority): ResultsDecisionPayload {
  let base: {
    top: { name: string; provider: string }
    alt1: { name: string; provider: string }
    alt2: { name: string; provider: string }
  }

  if (priority === "quality") {
    base = {
      top: { name: "Claude 3.5 Sonnet", provider: "Anthropic" },
      alt1: { name: "GPT-4o", provider: "OpenAI" },
      alt2: { name: "Gemini 1.5 Pro", provider: "Google" },
    }
  } else if (priority === "speed") {
    base = {
      top: { name: "GPT-4o mini", provider: "OpenAI" },
      alt1: { name: "Claude 3 Haiku", provider: "Anthropic" },
      alt2: { name: "Gemini 1.5 Flash", provider: "Google" },
    }
  } else {
    base = {
      top: { name: "Claude 3 Haiku", provider: "Anthropic" },
      alt1: { name: "GPT-4o mini", provider: "OpenAI" },
      alt2: { name: "Gemini 1.5 Flash", provider: "Google" },
    }
  }

  const mk = (id: string, n: string, p: string, score: number): ModelDecision => {
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
    } else if (id === "alt1") {
      metrics = { reasoning: 88, speed: 76, costEfficiency: 52, contextWindow: 70 }
    } else if (id === "alt2") {
      metrics = { reasoning: 84, speed: 66, costEfficiency: 58, contextWindow: 92 }
    } else {
      metrics = { reasoning: 70, speed: 55, costEfficiency: 95, contextWindow: 60 }
    }

    const actions =
      id === "free"
        ? [
            { kind: "runLocal", label: "Run locally" as const },
            { kind: "useFreeApi", label: "Use free API" as const },
          ]
        : undefined

    return {
      id,
      name: n,
      provider: p,
      score,
      latencyMs: undefined,
      cost: undefined,
      contextWindowTokens: undefined,
      why,
      pros,
      cons,
      metrics: normalizeMetrics(metrics),
      actions,
    }
  }

  return {
    topPick: mk("top", base.top.name, base.top.provider, 96),
    freeAlternative: mk("free", "Llama 3", "Open source", 74),
    alternatives: [
      mk("alt1", base.alt1.name, base.alt1.provider, 92),
      mk("alt2", base.alt2.name, base.alt2.provider, 90),
    ],
  }
}

export async function fetchRecommendation(
  req: RecommendRequest,
  opts?: { signal?: AbortSignal }
): Promise<ResultsDecisionPayload> {
  const controller = new AbortController()
  const signal = opts?.signal
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener("abort", () => controller.abort(), { once: true })
  }

  try {
    const res = await fetch("/api/recommend", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req),
      signal: controller.signal,
    })

    if (!res.ok) {
      throw new Error(`recommendation_failed_${res.status}`)
    }

    const json = (await res.json()) as ResultsDecisionPayload

    return {
      topPick: coerceModelDecision(json.topPick),
      freeAlternative: coerceModelDecision(json.freeAlternative),
      alternatives: Array.isArray(json.alternatives)
        ? json.alternatives.map(coerceModelDecision)
        : [],
    }
  } catch (e) {
    // Backend may not be wired yet; keep the UI usable.
    if (controller.signal.aborted) throw e
    return mockDecisionPayload(req.priority)
  }
}

