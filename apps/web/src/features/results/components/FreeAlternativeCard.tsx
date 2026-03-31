import { motion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import type { ModelDecision } from "@/features/results/types"
import type { TranslationKey } from "@/i18n/translations"
import { ModelCapabilityBadges } from "./ModelCapabilityBadges"
import { formatTokensCount, translateCatalogProCon } from "../utils"

function ActionButton({
  label,
  href,
}: Readonly<{ label: string; href?: string }>) {
  const className =
    "rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-4 py-2.5 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--surface-glass-hover) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"

  if (href) {
    return (
      <a
        className={className}
        href={href}
        target="_blank"
        rel="noreferrer"
      >
        {label}
      </a>
    )
  }

  return (
    <button type="button" className={className}>
      {label}
    </button>
  )
}

export function FreeAlternativeCard({
  model,
}: Readonly<{
  model: ModelDecision
}>) {
  const { t } = useI18n()

  const runLocal = model.actions?.find((a) => a.kind === "runLocal")
  const useFreeApi = model.actions?.find((a) => a.kind === "useFreeApi")
  const pros =
    model.pros.length > 0
      ? model.pros.map((p) => translateCatalogProCon(p, t))
      : [t("freeAltProNoCost"), t("freeAltProLocalOrFreeApi")]
  const cons =
    model.cons.length > 0
      ? model.cons.map((c) => translateCatalogProCon(c, t))
      : [t("freeAltConLowerAccuracy"), t("freeAltConSlower")]

  const formatUserRating = (value: number | undefined): string => {
    if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
    return value.toFixed(1)
  }
  const formatCostPerMillion = (value: number | undefined): string => {
    if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
    return value.toFixed(value >= 1 ? 2 : 4)
  }
  const priceLine =
    typeof model.costPerMillionInput === "number" &&
    Number.isFinite(model.costPerMillionInput) &&
    typeof model.costPerMillionOutput === "number" &&
    Number.isFinite(model.costPerMillionOutput)
      ? `$${formatCostPerMillion(model.costPerMillionInput)}/M in · $${formatCostPerMillion(model.costPerMillionOutput)}/M out`
      : model.cost?.rel ?? "N/A"

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-5 shadow-(--shadow-elevated) backdrop-blur-xl sm:p-6"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            {t("freeAlternative")}
          </p>
          <h3 className="mt-2 text-lg font-semibold text-(--text-primary) sm:text-xl">
            {model.name}
          </h3>
          <p className="mt-1 text-sm text-(--text-muted)">{model.provider}</p>
          <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-(--text-muted)">
            <span>★ {formatUserRating(model.userRating)}</span>
            <span className="text-(--border-subtle)">·</span>
            <span>{priceLine}</span>
          </div>
          <ModelCapabilityBadges model={model} className="mt-2" />
          {model.rankingReasonKey ? (
            <p className="mt-3 text-sm leading-relaxed text-(--text-muted)">
              {t(model.rankingReasonKey as TranslationKey)}
            </p>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-(--text-muted)">
            <span>
              <span className="uppercase tracking-wide">{t("labelContext")}: </span>
              <span className="font-medium tabular-nums text-(--text-primary)">
                {formatTokensCount(model.contextWindowTokens)}
              </span>
            </span>
            <span>
              <span className="uppercase tracking-wide">{t("labelOutputTokens")}: </span>
              <span className="font-medium tabular-nums text-(--text-primary)">
                {formatTokensCount(model.maxOutputTokens ?? undefined)}
              </span>
            </span>
          </div>
        </div>

        {(runLocal || useFreeApi) && (
          <div className="flex flex-wrap gap-2">
            {runLocal && (
              <ActionButton label={runLocal.label} href={runLocal.href} />
            )}
            {useFreeApi && (
              <ActionButton label={useFreeApi.label} href={useFreeApi.href} />
            )}
          </div>
        )}
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            {t("pros")}
          </p>
          <ul className="mt-2 space-y-1.5 text-sm text-(--text-primary)">
            {pros.slice(0, 4).map((p) => (
              <li key={p} className="flex gap-2">
                <span className="select-none text-emerald-400">✔</span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            {t("cons")}
          </p>
          <ul className="mt-2 space-y-1.5 text-sm text-(--text-primary)">
            {cons.slice(0, 4).map((c) => (
              <li key={c} className="flex gap-2">
                <span className="select-none text-rose-400">✖</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </motion.section>
  )
}

