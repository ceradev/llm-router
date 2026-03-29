import { motion } from "framer-motion"
import { useCallback, useMemo, useState } from "react"

import { useI18n } from "@/contexts/I18nContext"
import type { Priority } from "@/features/landing/types"
import {
  analyseButtonSpring,
  analyseHoverWhile,
  analyseShineTransition,
  analyseTapWhile,
} from "@/features/landing/config"
import type {
  CategoryPick,
  ModelDecision,
  ResultsDecisionPayload,
} from "@/features/results/types"
import type { TranslationKey } from "@/i18n/translations"
import { AppFooter, MainNavbar } from "@/shared/components"
import {
  formatLatency,
  formatTokensCount,
  getMockRankedModels,
  translateCatalogProCon,
  type RankedModel,
} from "./utils"
import { BenchmarkChart } from "./components/BenchmarkChart"
import { FreeAlternativeCard } from "./components/FreeAlternativeCard"
import { ModelCapabilityBadges } from "./components/ModelCapabilityBadges"

function costRelLabel(
  t: (k: TranslationKey) => string,
  rel: "low" | "medium" | "high",
) {
  if (rel === "low") return t("lowerCost")
  if (rel === "medium") return t("moderateCost")
  return t("higherCost")
}

function metricsForPriority(priority: Priority) {
  if (priority === "quality") {
    return { reasoning: 92, speed: 70, costEfficiency: 62, contextWindow: 78 }
  }
  if (priority === "speed") {
    return { reasoning: 78, speed: 92, costEfficiency: 78, contextWindow: 70 }
  }
  return { reasoning: 84, speed: 82, costEfficiency: 92, contextWindow: 70 }
}

function mockModelId(name: string): string {
  return `mock/${name.toLowerCase().replace(/\s+/g, "-")}`
}

function uniqueBenchmarkModels(models: ModelDecision[]): ModelDecision[] {
  const seen = new Set<string>()
  const out: ModelDecision[] = []
  for (const m of models) {
    if (seen.has(m.modelId)) continue
    seen.add(m.modelId)
    out.push(m)
  }
  return out
}

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
      const _exhaustive: never = kind
      return _exhaustive
    }
  }
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.06 },
  },
}

const item = {
  hidden: { opacity: 0, y: 14 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] },
  },
}

type Props = {
  prompt: string
  priority: Priority
  onNewAnalysis: () => void
  onStartOver: () => void
  onHistoryOpen: () => void
  historyOpen: boolean
  results?: ResultsDecisionPayload
}

function truncate(s: string, max: number) {
  const t = s.trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

export function ResultsView({
  prompt,
  priority,
  onNewAnalysis,
  onStartOver,
  onHistoryOpen,
  historyOpen,
  results,
}: Readonly<Props>) {
  const { t } = useI18n()
  const ranked = getMockRankedModels(priority)
  const rankedTop = ranked[0]
  const rankedRunners = ranked.slice(1)
  const [copied, setCopied] = useState(false)

  const deriveWhy = (top: RankedModel): string[] => {
    if (priority === "quality") {
      return [
        "More reliable multi-step reasoning on complex prompts.",
        "Better instruction-following when requirements are ambiguous.",
        "Higher success rate on long, structured outputs.",
      ]
    }
    if (priority === "speed") {
      return [
        "Lower latency for interactive iteration loops.",
        "Good enough reasoning for everyday tasks without the wait.",
        "Predictable response time under typical load.",
      ]
    }
    return [
      "Best cost/quality balance for your prompt shape.",
      "Lower per-call spend while keeping outputs usable.",
      "More efficient for frequent or batch usage.",
    ]
  }

  const toDecisionModel = (m: RankedModel, id: string): ModelDecision => ({
    id,
    modelId: mockModelId(m.name),
    name: m.name,
    provider: m.provider,
    score: m.score,
    latencyMs: m.latencyMs,
    cost: { rel: m.costRel },
    contextWindowTokens: 200_000,
    maxOutputTokens: 8192,
    why: id === "top" ? deriveWhy(m) : [],
    pros: [
      m.note,
      m.costRel === "low"
        ? "Lower relative cost for this priority."
        : "Strong overall performance.",
    ],
    cons: [
      m.costRel === "high"
        ? "Higher relative cost."
        : "Trade‑offs depend on workload and context size.",
    ],
    metrics: metricsForPriority(priority),
    actions: undefined,
    rankingReasonKey:
      id === "top" ? "rankingReasonBestOverallBalanced" : undefined,
  })

  const baseCategoryPicks: CategoryPick[] = rankedRunners.slice(0, 2).map((m, idx) => {
    const dm = toDecisionModel(m, `cat${idx}`)
    const kinds: CategoryPick["kind"][] = ["quality", "cost", "speed"]
    const kind = kinds[idx] ?? "quality"
    const keys: Record<CategoryPick["kind"], TranslationKey> = {
      quality: "rankingReasonCategoryQuality",
      cost: "rankingReasonCategoryCost",
      speed: "rankingReasonCategorySpeed",
    }
    return {
      kind,
      model: dm,
      reasonKey: keys[kind],
      sameAsBest: false,
    }
  })
  const filler = rankedRunners[1] ?? rankedTop
  const categoryPicksFallback: CategoryPick[] =
    baseCategoryPicks.length >= 3
      ? baseCategoryPicks.slice(0, 3)
      : [
          ...baseCategoryPicks,
          {
            kind: "speed",
            model: toDecisionModel(filler, "cat-speed"),
            reasonKey: "rankingReasonCategorySpeed",
            sameAsBest: false,
          },
        ]

  const fallbackPayload: ResultsDecisionPayload = {
    topPick: toDecisionModel(rankedTop, "top"),
    freeAlternative: {
      id: "free",
      modelId: mockModelId("Llama 3"),
      name: "Llama 3",
      provider: "Open source",
      score: Math.max(60, rankedTop.score - 20),
      latencyMs: undefined,
      cost: { rel: "low" },
      contextWindowTokens: 128_000,
      maxOutputTokens: 8192,
      why: [],
      pros: ["No usage cost.", "Runs locally or via free-tier APIs."],
      cons: ["Lower accuracy on hard tasks.", "Can be slower depending on hardware."],
      metrics: { reasoning: 70, speed: 55, costEfficiency: 95, contextWindow: 60 },
      actions: [
        { kind: "runLocal", label: "Run locally" },
        { kind: "useFreeApi", label: "Use free API" },
      ],
      rankingReasonKey: "rankingReasonFreeAlternative",
    },
    categoryPicks: categoryPicksFallback,
    extraAlternatives: rankedRunners.slice(0, 2).map((m, idx) =>
      toDecisionModel(m, `extra${idx + 1}`),
    ),
  }

  const payload = results ?? fallbackPayload
  const top = payload.topPick
  const runners = payload.extraAlternatives

  const benchmarkModels = useMemo(
    () =>
      uniqueBenchmarkModels([
        payload.topPick,
        ...(payload.freeAlternative ? [payload.freeAlternative] : []),
        ...payload.categoryPicks.map((c) => c.model),
      ]),
    [payload],
  )

  const handleCopy = useCallback(() => {
    const why = top.why?.length ? `\nWhy:\n- ${top.why.join("\n- ")}` : ""
    const text = `Recommended: ${top.name} (${top.provider})\nMatch: ${top.score}%${why}`
    void navigator.clipboard.writeText(text).then(
      () => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      },
      () => {
        setCopied(false)
      },
    )
  }, [top])

  return (
    <motion.div
      className="relative z-10 mx-auto flex min-h-dvh max-w-4xl flex-col px-4 pb-16 pt-6 sm:px-6 sm:pt-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.35 }}
    >
      <div className="flex-1">
        <MainNavbar
          className="mb-8 flex justify-center sm:mb-10"
          onHistoryOpen={onHistoryOpen}
          historyOpen={historyOpen}
        />

        <motion.header
          variants={container}
          initial="hidden"
          animate="show"
          className="mb-8 text-center sm:mb-10"
        >
          <motion.p
            variants={item}
            className="text-[12px] font-semibold uppercase tracking-wider text-(--text-accent)"
          >
            {t("resultLabel")}
          </motion.p>
          <motion.h1
            variants={item}
            className="mt-2 text-2xl font-semibold tracking-tight text-(--text-primary) sm:text-3xl"
          >
            {t("resultTitle")}
          </motion.h1>
          <motion.p
            variants={item}
            className="mx-auto mt-3 max-w-lg text-base leading-relaxed text-(--text-muted)"
          >
            {t("resultBasedOn")}{" "}
            <span className="capitalize text-(--text-primary)">
              {t(priority)}
            </span>{" "}
            {t("resultPriority")}
          </motion.p>
        </motion.header>

        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-elevated) backdrop-blur-xl sm:p-5"
        >
          <motion.p
            variants={item}
            className="text-[12px] font-medium uppercase tracking-wide text-(--text-muted)"
          >
            {t("yourPrompt")}
          </motion.p>
          <motion.p
            variants={item}
            className="mt-1.5 text-base leading-relaxed text-(--text-primary)"
          >
            {truncate(prompt, 220)}
          </motion.p>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="mt-6 space-y-4"
        >
          <motion.section
            variants={item}
            className="rounded-xl border border-(--border-subtle) bg-(--surface-glass)/80 p-4 text-sm leading-relaxed text-(--text-muted) backdrop-blur-sm sm:p-5"
          >
            <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-muted)">
              {t("modelsLegendTitle")}
            </p>
            <ul className="mt-3 grid gap-2 sm:grid-cols-2">
              <li>
                <span className="font-medium text-(--text-primary)">{t("quality")}: </span>
                {t("legendQuality")}
              </li>
              <li>
                <span className="font-medium text-(--text-primary)">{t("cost")}: </span>
                {t("legendCost")}
              </li>
              <li>
                <span className="font-medium text-(--text-primary)">{t("speed")}: </span>
                {t("legendSpeed")}
              </li>
              <li>
                <span className="font-medium text-(--text-primary)">
                  {t("labelOutputTokens")}:{" "}
                </span>
                {t("legendTokens")}
              </li>
              <li className="sm:col-span-2">
                <span className="font-medium text-(--text-primary)">
                  {t("labelContext")}:{" "}
                </span>
                {t("legendContext")}
              </li>
            </ul>
          </motion.section>

          <motion.div
            variants={item}
            className="relative overflow-hidden rounded-2xl border border-[#3B82F6]/30 bg-linear-to-br from-[#3B82F6]/15 via-(--surface-glass) to-[#0EA5E9]/10 p-5 shadow-[0_0_40px_rgba(59,130,246,0.12)] backdrop-blur-xl sm:p-6"
          >
            <div
              className="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-[#0EA5E9]/20 blur-2xl"
              aria-hidden
            />
            <div className="relative">
              <span className="inline-flex items-center rounded-full bg-(--badge-bg) px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-(--text-accent-secondary)">
                {t("bestModel")}
              </span>
              <h2 className="mt-3 text-xl font-semibold text-(--text-primary) sm:text-2xl">
                {top.name}
              </h2>
              <p className="mt-1 text-base text-(--text-accent)">{top.provider}</p>
              <ModelCapabilityBadges model={top} className="mt-3" />
              {top.rankingReasonKey ? (
                <p className="mt-3 text-sm leading-relaxed text-(--text-muted)">
                  {t(top.rankingReasonKey as TranslationKey)}
                </p>
              ) : null}
              {!top.rankingReasonKey && top.why?.length > 0 ? (
                <div className="mt-4">
                  <p className="text-[12px] font-semibold uppercase tracking-wider text-(--text-muted)">
                    {t("whyThisModel")}
                  </p>
                  <ul className="mt-2 space-y-1.5 text-base leading-relaxed text-(--text-muted)">
                    {top.why.slice(0, 5).map((w) => (
                      <li key={w} className="flex gap-2">
                        <span className="mt-0.5 select-none text-(--text-accent)">•</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {!top.rankingReasonKey && (top.why?.length ?? 0) === 0 ? (
                <p className="mt-4 text-base leading-relaxed text-(--text-muted)">
                  {t("whyThisModelFallback")}
                </p>
              ) : null}
              {top.rankingReasonKey && top.why?.length > 0 ? (
                <div className="mt-4 border-t border-(--border-subtle) pt-4">
                  <p className="text-[12px] font-semibold uppercase tracking-wider text-(--text-muted)">
                    {t("whyThisModel")}
                  </p>
                  <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-(--text-muted)">
                    {top.why.slice(0, 3).map((w) => (
                      <li key={w} className="flex gap-2">
                        <span className="mt-0.5 select-none text-(--text-accent)">•</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {top.rankingExplanation ? (
                <details className="mt-4 rounded-lg border border-(--border-subtle) bg-(--surface-glass) px-3 py-2 text-left">
                  <summary className="cursor-pointer text-[12px] font-semibold text-(--text-muted)">
                    {t("scoringDetailTitle")}
                  </summary>
                  <p className="mt-2 font-mono text-[11px] leading-relaxed break-words text-(--text-muted)">
                    {top.rankingExplanation}
                  </p>
                </details>
              ) : null}

              <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-(--border-subtle) pt-5 text-center sm:grid-cols-3 sm:gap-4">
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-(--text-muted)">
                    {t("match")}
                  </dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums text-(--text-primary)">
                    {top.score}%
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-(--text-muted)">
                    {t("latency")}
                  </dt>
                  <dd className="mt-1 text-base font-medium tabular-nums text-(--text-primary)">
                    {typeof top.latencyMs === "number"
                      ? formatLatency(top.latencyMs)
                      : t("unknownLatency")}
                  </dd>
                </div>
                <div className="col-span-2 sm:col-span-1">
                  <dt className="text-[11px] uppercase tracking-wide text-(--text-muted)">
                    {t("costLabel")}
                  </dt>
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
              </div>
            </div>
          </motion.div>

          {payload.freeAlternative ? (
            <motion.div variants={item}>
              <FreeAlternativeCard model={payload.freeAlternative} />
            </motion.div>
          ) : null}

          <motion.section variants={item} className="space-y-3">
            <div>
              <p className="text-[12px] font-semibold uppercase tracking-wider text-(--text-muted)">
                {t("alternativesByCategory")}
              </p>
              <p className="mt-1 text-sm text-(--text-muted)">{t("rankingOverviewLine")}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {payload.categoryPicks.map((pick) => (
                <CategoryHighlightCard key={pick.kind} pick={pick} t={t} />
              ))}
            </div>
          </motion.section>

          <motion.div variants={item}>
            <BenchmarkChart models={benchmarkModels} />
          </motion.div>

          {runners.length > 0 ? (
            <motion.div variants={item}>
              <p className="mb-3 text-[12px] font-semibold uppercase tracking-wider text-(--text-muted)">
                {t("otherAlternativesSection")}
              </p>
              <ul className="space-y-2">
                {runners.map((m, i) => (
                  <RunnerRow key={m.id ?? m.name} model={m} index={i} />
                ))}
              </ul>
            </motion.div>
          ) : null}
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-center"
        >
          <motion.button
            variants={item}
            type="button"
            onClick={handleCopy}
            className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-5 py-3 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--surface-glass-hover) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
          >
            {copied ? t("copied") : t("copyRecommendation")}
          </motion.button>
          <motion.button
            variants={item}
            type="button"
            onClick={onNewAnalysis}
            whileHover={analyseHoverWhile}
            whileTap={analyseTapWhile}
            transition={analyseButtonSpring}
            className="relative overflow-hidden rounded-xl bg-[linear-gradient(135deg,#3B82F6,#1E40AF)] bg-size-[200%_200%] bg-left px-8 py-3.5 text-sm font-semibold text-white transition-all cursor-pointer duration-50 disabled:cursor-not-allowed disabled:opacity-40 sm:px-10 sm:py-4 sm:text-base focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
          >
            <span className="relative z-10">{t("newAnalysis")}</span>

            <motion.span
              className="absolute inset-0 bg-linear-to-r from-white/0 via-white/10 to-white/0"
              initial={{ x: "-100%" }}
              whileHover={{ x: "100%" }}
              transition={analyseShineTransition}
            />
          </motion.button>
          <motion.button
            variants={item}
            type="button"
            onClick={onStartOver}
            className="rounded-xl px-5 py-3 text-sm font-medium text-(--text-muted) transition-colors hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-subtle)"
          >
            {t("startOver")}
          </motion.button>
        </motion.div>
      </div>

      <AppFooter className="mt-8 sm:mt-10" />
    </motion.div>
  )
}

function CategoryHighlightCard({
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
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
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
      {model.rankingExplanation ? (
        <p className="mt-2 text-[11px] leading-relaxed text-(--text-muted)">
          <span className="font-semibold text-(--text-primary)">{t("rankingScoreExplanation")}: </span>
          {truncate(model.rankingExplanation, 200)}
        </p>
      ) : null}
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

function RunnerRow({
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
          {model.rankingExplanation ? (
            <p className="mt-2 text-[11px] leading-relaxed text-(--text-muted)">
              <span className="font-semibold text-(--text-primary)">{t("rankingScoreExplanation")}: </span>
              {truncate(model.rankingExplanation, 220)}
            </p>
          ) : null}
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
            {model.score}%
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
