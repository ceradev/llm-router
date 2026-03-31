import { motion } from "framer-motion"

import type { ModelDecision, ResultsDecisionPayload } from "@/features/results/types"
import type { TranslationKey } from "@/i18n/translations"
import { formatLatency, formatTokensCount } from "../utils"
import { ModelCapabilityBadges } from "./ModelCapabilityBadges"

type TFn = (k: TranslationKey) => string

function costRelLabel(
  t: (k: TranslationKey) => string,
  rel: "low" | "medium" | "high",
) {
  if (rel === "low") return t("lowerCost")
  if (rel === "medium") return t("moderateCost")
  return t("higherCost")
}

function formatCostPerMillion(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  return value.toFixed(value >= 1 ? 2 : 4)
}

function formatTopCostPrices(model: ModelDecision): string | null {
  if (
    typeof model.costPerMillionInput === "number" &&
    Number.isFinite(model.costPerMillionInput) &&
    typeof model.costPerMillionOutput === "number" &&
    Number.isFinite(model.costPerMillionOutput)
  ) {
    return `$${formatCostPerMillion(model.costPerMillionInput)}/M in · $${formatCostPerMillion(model.costPerMillionOutput)}/M out`
  }
  return null
}

function formatScoreOutOfTen(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  const clamped = Math.max(1, Math.min(10, value))
  return clamped.toFixed(1)
}

function formatUserRating(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  return value.toFixed(1)
}

export function TopModelCard({
  top,
  routing,
  isMock,
  t,
  variants,
}: Readonly<{
  top: ModelDecision
  routing: ResultsDecisionPayload["routing"]
  isMock: boolean
  t: TFn
  variants: object
}>) {
  return (
    <motion.div
      variants={variants}
      className="relative overflow-hidden rounded-2xl border border-[#3B82F6]/30 bg-linear-to-br from-[#3B82F6]/15 via-(--surface-glass) to-[#0EA5E9]/10 p-5 backdrop-blur-xl sm:p-6"
    >
      <div
        className="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-[#0EA5E9]/20 blur-2xl"
        aria-hidden
      />
      <div className="relative">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span className="inline-flex items-center rounded-full bg-(--badge-bg) px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-(--text-accent-secondary)">
              {t("bestModel")}
            </span>
            <h2 className="mt-3 truncate text-xl font-semibold text-(--text-primary) sm:text-2xl">{top.name}</h2>
            <p className="mt-1 truncate text-base text-(--text-accent)">{top.provider}</p>
          </div>
          <div className="shrink-0 text-right">
            <div className="flex items-baseline justify-end gap-4">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-sky-100/80">Score</p>
                <p className="text-lg font-semibold tabular-nums text-sky-100">{formatScoreOutOfTen(top.score)}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-100/75">Rating</p>
                <p className="text-sm font-medium tabular-nums text-violet-100">★ {formatUserRating(top.userRating)}</p>
              </div>
            </div>
          </div>
        </div>

        <WhyThisModelSection top={top} routing={routing} isMock={isMock} t={t} />

        <ModelCapabilityBadges model={top} className="mt-5" />

        <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-(--border-subtle) pt-5 text-center sm:grid-cols-3 sm:gap-4">
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-(--text-muted)">Score</dt>
            <dd className="mt-1 text-lg font-semibold tabular-nums text-(--text-primary)">
              {formatScoreOutOfTen(top.score)}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-(--text-muted)">{t("latency")}</dt>
            <dd className="mt-1 text-base font-medium tabular-nums text-(--text-primary)">
              {typeof top.latencyMs === "number" ? formatLatency(top.latencyMs) : t("unknownLatency")}
            </dd>
          </div>
          <div className="col-span-2 sm:col-span-1">
            <dt className="text-[11px] uppercase tracking-wide text-(--text-muted)">{t("costLabel")}</dt>
            <dd className="mt-1 text-base font-medium text-(--text-primary)">
              {top.cost?.rel ? costRelLabel(t, top.cost.rel) : t("unknownCost")}
            </dd>
          </div>
        </dl>
        <div className="mt-4 flex flex-wrap gap-4 border-t border-(--border-subtle) pt-4 text-sm">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-(--text-muted)">
              {t("labelContext")}
            </p>
            <p className="mt-0.5 font-medium tabular-nums text-(--text-primary)">
              {formatTokensCount(top.contextWindowTokens)}
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-(--text-muted)">
              {t("labelOutputTokens")}
            </p>
            <p className="mt-0.5 font-medium tabular-nums text-(--text-primary)">
              {formatTokensCount(top.maxOutputTokens ?? undefined)}
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-(--text-muted)">Pricing</p>
            <p className="mt-0.5 font-medium text-(--text-primary)">{formatTopCostPrices(top) ?? "N/A"}</p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function WhyThisModelSection({
  top,
  routing,
  isMock,
  t,
}: Readonly<{
  top: ModelDecision
  routing: ResultsDecisionPayload["routing"]
  isMock: boolean
  t: TFn
}>) {
  const hasRankingReason = Boolean(top.rankingReasonKey)
  const hasRoutingReason = Boolean(routing?.routingReason) && !isMock
  const hasWhyBullets = !hasRankingReason && !hasRoutingReason && (top.why?.length ?? 0) > 0
  const showFallbackWhy = !hasRankingReason && !hasRoutingReason && !hasWhyBullets && isMock

  return (
    <div className="mt-5">
      <p className="text-[12px] font-semibold uppercase tracking-wider text-(--text-muted)">
        {t("whyThisModel")}
      </p>
      {hasRankingReason && top.rankingReasonKey ? (
        <p className="mt-2 text-base leading-relaxed text-(--text-primary)">
          {t(top.rankingReasonKey as TranslationKey)}
        </p>
      ) : null}
      {!hasRankingReason && hasRoutingReason ? (
        <p className="mt-2 text-base leading-relaxed text-(--text-primary)">{routing?.routingReason}</p>
      ) : null}
      {hasRankingReason && hasRoutingReason ? (
        <p className="mt-2 text-sm leading-relaxed text-(--text-muted)">{routing?.routingReason}</p>
      ) : null}
      {hasWhyBullets ? (
        <ul className="mt-2 space-y-1.5 text-base leading-relaxed text-(--text-muted)">
          {top.why.slice(0, 5).map((w) => (
            <li key={w} className="flex gap-2">
              <span className="mt-0.5 select-none text-(--text-accent)">•</span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {showFallbackWhy ? (
        <p className="mt-2 text-base leading-relaxed text-(--text-muted)">{t("whyThisModelFallback")}</p>
      ) : null}
    </div>
  )
}
