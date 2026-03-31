import { motion } from "framer-motion"

import type { CategoryPick } from "@/features/results/types"
import type { TranslationKey } from "@/i18n/translations"
import { formatTokensCount } from "../utils"
import { ModelCapabilityBadges } from "./ModelCapabilityBadges"

function categoryTitle(
  t: (k: TranslationKey) => string,
  kind: CategoryPick["kind"],
): string {
  switch (kind) {
    case "quality":
      return t("categoryLabelQuality")
    case "cost":
      return t("categoryLabelCost")
    case "speed":
      return t("categoryLabelSpeed")
    default: {
      const exhaustive: never = kind
      return exhaustive
    }
  }
}

function formatUserRating(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  return value.toFixed(1)
}

function formatCostPerMillion(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  return value.toFixed(value >= 1 ? 2 : 4)
}

function formatPriceLine(model: CategoryPick["model"]): string {
  if (
    typeof model.costPerMillionInput === "number" &&
    Number.isFinite(model.costPerMillionInput) &&
    typeof model.costPerMillionOutput === "number" &&
    Number.isFinite(model.costPerMillionOutput)
  ) {
    return `$${formatCostPerMillion(model.costPerMillionInput)}/M · $${formatCostPerMillion(model.costPerMillionOutput)}/M`
  }
  return model.cost?.rel ?? "N/A"
}

function formatScoreOutOfTen(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  const clamped = Math.max(1, Math.min(10, value))
  return clamped.toFixed(1)
}

export function CategoryHighlightCard({
  pick,
  t,
}: Readonly<{
  pick: CategoryPick
  t: (k: TranslationKey) => string
}>) {
  const { model } = pick
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] as const }}
      className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) p-5 backdrop-blur-sm sm:p-6"
    >
      <p className="text-[12px] font-semibold uppercase tracking-wide text-(--text-accent)">
        {categoryTitle(t, pick.kind)}
      </p>
      <p className="mt-2 truncate text-lg font-semibold text-(--text-primary)">{model.name}</p>
      <p className="truncate text-sm text-(--text-muted)">{model.provider}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-(--text-muted)">
        <span>Score {formatScoreOutOfTen(model.score)}</span>
        <span className="text-(--border-subtle)">·</span>
        <span>★ {formatUserRating(model.userRating)}</span>
        <span className="text-(--border-subtle)">·</span>
        <span>{formatPriceLine(model)}</span>
      </div>
      {pick.sameAsBest ? (
        <p className="mt-3 rounded-lg bg-(--badge-bg) px-2.5 py-1 text-[11px] font-medium text-(--text-accent-secondary)">
          {t("rankingSameAsBestModel")}
        </p>
      ) : null}
      <p className="mt-3 text-sm leading-relaxed text-(--text-muted)">
        {t(pick.reasonKey as TranslationKey)}
      </p>
      <ModelCapabilityBadges model={model} className="mt-3" />
      <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 border-t border-(--border-subtle) pt-4 text-[11px] text-(--text-muted)">
        <span>
          <span className="text-(--text-muted)">{t("labelContext")}: </span>
          <span className="font-medium tabular-nums text-(--text-primary)">
            {formatTokensCount(model.contextWindowTokens)}
          </span>
        </span>
        <span>
          <span className="text-(--text-muted)">{t("labelOutputTokens")}: </span>
          <span className="font-medium tabular-nums text-(--text-primary)">
            {formatTokensCount(model.maxOutputTokens ?? undefined)}
          </span>
        </span>
      </div>
    </motion.div>
  )
}
