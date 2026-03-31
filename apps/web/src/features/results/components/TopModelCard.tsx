import { motion } from "framer-motion"

import type { ModelDecision, ResultsDecisionPayload } from "@/features/results/types"
import type { TranslationKey } from "@/i18n/translations"
import { formatLatency, formatTokensCount } from "../utils"
import { ModelCapabilityBadges } from "./ModelCapabilityBadges"

type TFn = (k: TranslationKey) => string
type FeedbackState = "idle" | "submitting" | "success" | "error"

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

function formatUserRating(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  return value.toFixed(1)
}

function formatScoreOutOfTen(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A"
  const clamped = Math.max(1, Math.min(10, value))
  return clamped.toFixed(1)
}

export function TopModelCard({
  top,
  routing,
  isMock,
  canSendFeedback,
  feedbackRating,
  feedbackState,
  onRate,
  t,
  variants,
}: Readonly<{
  top: ModelDecision
  routing: ResultsDecisionPayload["routing"]
  isMock: boolean
  canSendFeedback: boolean
  feedbackRating: number | null
  feedbackState: FeedbackState
  onRate: (rating: number) => void
  t: TFn
  variants: object
}>) {
  const feedbackDisabledHintVisible = canSendFeedback === false

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
        <div className="absolute right-0 top-0 min-w-28 text-right">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-sky-100/80">Score</p>
          <p className="text-lg font-semibold tabular-nums text-sky-100">{formatScoreOutOfTen(top.score)}</p>
          <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-violet-100/75">Rating</p>
          <p className="text-sm font-medium tabular-nums text-violet-100">★ {formatUserRating(top.userRating)}</p>
        </div>
        <span className="inline-flex items-center rounded-full bg-(--badge-bg) px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-(--text-accent-secondary)">
          {t("bestModel")}
        </span>
        <h2 className="mt-3 text-xl font-semibold text-(--text-primary) sm:text-2xl">{top.name}</h2>
        <p className="mt-1 text-base text-(--text-accent)">{top.provider}</p>

        <WhyThisModelSection top={top} routing={routing} isMock={isMock} t={t} />

        <ModelCapabilityBadges model={top} className="mt-5" />

        <div className="mt-4 rounded-lg border border-(--border-subtle) bg-(--surface-glass) px-3 py-3 text-left">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-(--text-muted)">User rating</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {[1, 2, 3, 4, 5].map((value) => (
              <button
                key={value}
                type="button"
                disabled={!canSendFeedback || feedbackState === "submitting"}
                onClick={() => onRate(value)}
                className={
                  feedbackRating === value
                    ? "rounded-md border border-sky-300/60 bg-sky-500/20 px-2.5 py-1 text-xs font-semibold text-sky-100 disabled:opacity-50"
                    : "rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2.5 py-1 text-xs font-medium text-(--text-primary) disabled:opacity-50"
                }
              >
                {value}
              </button>
            ))}
          </div>
          {feedbackDisabledHintVisible ? (
            <p className="mt-2 text-[11px] text-(--text-muted)">
              Feedback available for backend-ranked results only.
            </p>
          ) : null}
          {feedbackState === "success" ? (
            <p className="mt-2 text-[11px] text-emerald-300">Thanks for your feedback.</p>
          ) : null}
          {feedbackState === "error" ? (
            <p className="mt-2 text-[11px] text-rose-300">Unable to save feedback right now.</p>
          ) : null}
        </div>

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
