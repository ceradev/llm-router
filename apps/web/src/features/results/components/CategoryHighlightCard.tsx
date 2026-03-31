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
      className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) p-4 backdrop-blur-sm"
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-(--text-accent)">
        {categoryTitle(t, pick.kind)}
      </p>
      <p className="mt-2 truncate text-base font-semibold text-(--text-primary)">{model.name}</p>
      <p className="truncate text-xs text-(--text-muted)">{model.provider}</p>
      {pick.sameAsBest ? (
        <p className="mt-2 rounded-lg bg-(--badge-bg) px-2 py-1 text-[11px] font-medium text-(--text-accent-secondary)">
          {t("rankingSameAsBestModel")}
        </p>
      ) : null}
      <p className="mt-2 text-xs leading-relaxed text-(--text-muted)">
        {t(pick.reasonKey as TranslationKey)}
      </p>
      <ModelCapabilityBadges model={model} className="mt-2" />
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 border-t border-(--border-subtle) pt-3 text-[11px] text-(--text-muted)">
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
