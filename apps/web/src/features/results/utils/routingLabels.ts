import type { TranslationKey } from "@/i18n/translations"

const INTENT: Record<string, TranslationKey> = {
  general: "intentGeneral",
  analysis: "intentAnalysis",
  code: "intentCode",
  creative: "intentCreative",
}

const PRIORITY: Record<string, TranslationKey> = {
  balanced: "priorityBalanced",
  high_quality: "priorityHighQuality",
  low_latency: "priorityLowLatency",
  low_cost: "priorityLowCost",
}

export function labelIntent(raw: string, t: (k: TranslationKey) => string): string {
  const k = INTENT[raw]
  return k ? t(k) : raw.replace(/_/g, " ")
}

export function labelPriority(raw: string, t: (k: TranslationKey) => string): string {
  const k = PRIORITY[raw]
  return k ? t(k) : raw.replace(/_/g, " ")
}

export function shortModelId(modelId: string): string {
  const tail = modelId.split("/").pop() ?? modelId
  return tail.replace(/-/g, " ")
}

const CAP: Record<string, TranslationKey> = {
  general: "cap_general",
  analysis: "cap_analysis",
  code: "cap_code",
  creative: "cap_creative",
  json: "cap_json",
}

export function labelCapability(
  cap: string,
  t: (k: TranslationKey) => string,
): string {
  const k = CAP[cap]
  return k ? t(k) : cap
}
