import { motion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import type { ModelDecision } from "@/features/results/types"
import type { TranslationKey } from "@/i18n/translations"
import { formatLatency, formatTokensCount, translateCatalogProCon } from "../utils"
import { ModelCapabilityBadges } from "./ModelCapabilityBadges"

function costRelLabel(
  t: (k: TranslationKey) => string,
  rel: "low" | "medium" | "high",
) {
  if (rel === "low") return t("lowerCost")
  if (rel === "medium") return t("moderateCost")
  return t("higherCost")
}

function formatScoreOutOfTen(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  const clamped = Math.max(1, Math.min(10, value))
  return clamped.toFixed(1)
}

export function RunnerRow({
  model,
  index,
}: Readonly<{ model: ModelDecision; index: number }>) {
  const { t } = useI18n()
  const pros = model.pros.map((p) => translateCatalogProCon(p, t))
  const cons = model.cons.map((c) => translateCatalogProCon(c, t))

  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.12 + index * 0.06, duration: 0.3 }}
      className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-4 py-3 backdrop-blur-sm transition-colors hover:border-(--surface-glass-hover) hover:bg-(--surface-glass-hover)"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate text-base font-semibold text-(--text-primary)">{model.name}</p>
          <p className="text-[12px] text-(--text-muted)">{model.provider}</p>
          <ModelCapabilityBadges model={model} className="mt-2" />
          <p className="mt-2 text-[11px] text-(--text-muted)">
            <span className="text-(--text-muted)">{t("labelContext")}: </span>
            <span className="font-medium tabular-nums text-(--text-primary)">
              {formatTokensCount(model.contextWindowTokens)}
            </span>
            <span className="mx-2 text-(--border-subtle)">·</span>
            <span className="text-(--text-muted)">{t("labelOutputTokens")}: </span>
            <span className="font-medium tabular-nums text-(--text-primary)">
              {formatTokensCount(model.maxOutputTokens ?? undefined)}
            </span>
          </p>

          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-muted)">
                {t("pros")}
              </p>
              <ul className="mt-1 space-y-1 text-[12px] text-(--text-primary)">
                {pros.slice(0, 2).map((p) => (
                  <li key={p} className="flex gap-2">
                    <span className="select-none text-emerald-400">✔</span>
                    <span className="min-w-0 truncate">{p}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-muted)">
                {t("cons")}
              </p>
              <ul className="mt-1 space-y-1 text-[12px] text-(--text-primary)">
                {cons.slice(0, 2).map((c) => (
                  <li key={c} className="flex gap-2">
                    <span className="select-none text-rose-400">✖</span>
                    <span className="min-w-0 truncate">{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="shrink-0 text-right">
          <p className="text-base font-semibold tabular-nums text-(--text-primary)">
            {formatScoreOutOfTen(model.score)}
          </p>
          <p className="text-[11px] text-(--text-muted)">
            {typeof model.latencyMs === "number"
              ? formatLatency(model.latencyMs)
              : t("unknownLatency")}
          </p>
          <p className="mt-0.5 text-[11px] text-(--text-muted)">
            {model.cost?.rel ? costRelLabel(t, model.cost.rel) : t("unknownCost")}
          </p>
        </div>
      </div>
    </motion.li>
  )
}
