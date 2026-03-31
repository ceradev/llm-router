import type { TranslationKey } from "@/i18n/translations"

const PRO_CON_MAP: Record<string, TranslationKey> = {
  strong_quality_profile: "proStrongQualityProfile",
  limited_quality_profile: "conLimitedQualityProfile",
  low_latency_profile: "proLowLatencyProfile",
  economical_profile: "proEconomicalProfile",
  higher_cost_for_low_cost_priority: "conHigherCostForLowCostPriority",
}

export function translateCatalogProCon(
  line: string,
  t: (k: TranslationKey) => string,
): string {
  const k = PRO_CON_MAP[line.trim()]
  return k ? t(k) : line
}
