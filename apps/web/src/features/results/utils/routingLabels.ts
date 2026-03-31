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
  return k ? t(k) : raw.replaceAll("_", " ")
}

export function labelPriority(raw: string, t: (k: TranslationKey) => string): string {
  const k = PRIORITY[raw]
  return k ? t(k) : raw.replaceAll("_", " ")
}

export function shortModelId(modelId: string): string {
  const tail = modelId.split("/").pop() ?? modelId
  return tail.replaceAll("-", " ")
}

const CAP: Record<string, TranslationKey> = {
  general: "cap_general",
  chat: "typeLabel_chat",
  analysis: "cap_analysis",
  code: "cap_code",
  creative: "cap_creative",
  multimodal_general: "typeLabel_multimodal",
  vision: "typeLabel_vision",
  json: "cap_json",
}

export function labelCapability(
  cap: string,
  t: (k: TranslationKey) => string,
): string {
  const k = CAP[cap]
  return k ? t(k) : cap
}

const TYPE_LABEL: Record<string, TranslationKey> = {
  chat: "typeLabel_chat",
  code: "typeLabel_code",
  analysis: "typeLabel_analysis",
  json: "typeLabel_json",
  tools: "typeLabel_tools",
  multimodal: "typeLabel_multimodal",
  vision: "typeLabel_vision",
}

export function labelModelTypeLabel(
  key: string,
  t: (k: TranslationKey) => string,
): string {
  const k = TYPE_LABEL[key]
  return k ? t(k) : key
}

const PUBLIC_STATUS: Record<string, TranslationKey> = {
  verified: "publicStatus_verified",
  provisional: "publicStatus_provisional",
  available: "publicStatus_available",
  deprecated: "publicStatus_deprecated",
}

export function labelPublicStatus(
  key: string,
  t: (k: TranslationKey) => string,
): string {
  const k = PUBLIC_STATUS[key]
  return k ? t(k) : key
}
