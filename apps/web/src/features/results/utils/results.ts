import type { Priority } from "../../hero/types/routingOptions"

export type RankedModel = {
  rank: number
  name: string
  provider: string
  score: number
  latencyMs: number
  costRel: "low" | "medium" | "high"
  note: string
}

export function getMockRankedModels(priority: Priority): RankedModel[] {
  const byPriority: Record<Priority, RankedModel[]> = {
    quality: [
      {
        rank: 1,
        name: "Claude 3.5 Sonnet",
        provider: "Anthropic",
        score: 96,
        latencyMs: 780,
        costRel: "medium",
        note: "Strong reasoning and instruction-following for complex tasks.",
      },
      {
        rank: 2,
        name: "GPT-4o",
        provider: "OpenAI",
        score: 94,
        latencyMs: 620,
        costRel: "high",
        note: "Excellent multimodal depth; great default for ambiguous prompts.",
      },
      {
        rank: 3,
        name: "Gemini 1.5 Pro",
        provider: "Google",
        score: 91,
        latencyMs: 890,
        costRel: "medium",
        note: "Long-context strength when your payload is large.",
      },
    ],
    speed: [
      {
        rank: 1,
        name: "GPT-4o mini",
        provider: "OpenAI",
        score: 88,
        latencyMs: 210,
        costRel: "low",
        note: "Low latency with solid quality for most everyday prompts.",
      },
      {
        rank: 2,
        name: "Claude 3 Haiku",
        provider: "Anthropic",
        score: 85,
        latencyMs: 240,
        costRel: "low",
        note: "Snappy responses; ideal for tight iteration loops.",
      },
      {
        rank: 3,
        name: "Gemini 1.5 Flash",
        provider: "Google",
        score: 84,
        latencyMs: 260,
        costRel: "low",
        note: "High throughput when you need volume and speed.",
      },
    ],
    cost: [
      {
        rank: 1,
        name: "Claude 3 Haiku",
        provider: "Anthropic",
        score: 82,
        latencyMs: 280,
        costRel: "low",
        note: "Best cost/quality balance for structured, shorter tasks.",
      },
      {
        rank: 2,
        name: "GPT-4o mini",
        provider: "OpenAI",
        score: 81,
        latencyMs: 220,
        costRel: "low",
        note: "Predictable pricing with broad tool compatibility.",
      },
      {
        rank: 3,
        name: "Gemini 1.5 Flash",
        provider: "Google",
        score: 79,
        latencyMs: 300,
        costRel: "low",
        note: "Economical at scale for batch-style workloads.",
      },
    ],
  }

  return byPriority[priority]
}

export function formatLatency(ms: number): string {
  if (ms < 1000) return `~${ms} ms`
  return `~${(ms / 1000).toFixed(1)} s`
}

export function costLabel(rel: RankedModel["costRel"]): string {
  if (rel === "low") return "Lower cost"
  if (rel === "medium") return "Moderate cost"
  return "Higher cost"
}

