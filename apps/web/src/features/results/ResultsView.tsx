import { motion } from "framer-motion"
import { useCallback, useMemo, useState } from "react"

import { useI18n } from "@/contexts/I18nContext"
import type { Priority } from "@/features/landing/types"
import { submitModelFeedback } from "@/shared/api/modelFeedback"
import {
  analyseButtonSpring,
  analyseHoverWhile,
  analyseShineTransition,
  analyseTapWhile,
} from "@/features/landing/config"
import type {
  ResultsDecisionPayload,
} from "@/features/results/types"
import { AppFooter, MainNavbar } from "@/shared/components"
import {
  getMockRankedModels,
} from "./utils"
import { BenchmarkChart } from "./components/BenchmarkChart"
import { CategoryHighlightCard } from "./components/CategoryHighlightCard"
import { FreeAlternativeCard } from "./components/FreeAlternativeCard"
import { RunnerRow } from "./components/RunnerRow"
import { TopModelCard } from "./components/TopModelCard"
import {
  buildBenchmarkModels,
  buildFallbackPayload,
  buildProvidersBanner,
  formatScoreOutOfTen,
  truncateText,
} from "./utils/resultsView"

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
    transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as const },
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

type FeedbackState = "idle" | "submitting" | "success" | "error"

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
  const [copied, setCopied] = useState(false)
  const [feedbackRating, setFeedbackRating] = useState<number | null>(null)
  const [feedbackState, setFeedbackState] = useState<FeedbackState>("idle")

  const fallbackPayload = useMemo(
    () => buildFallbackPayload(priority, ranked),
    [priority, ranked],
  )

  const payload = results ?? fallbackPayload
  const top = payload.topPick
  const runners = payload.extraAlternatives
  const routing = payload.routing

  const providersBanner = useMemo(() => buildProvidersBanner(routing), [routing])

  const benchmarkModels = useMemo(() => buildBenchmarkModels(payload), [payload])

  const handleCopy = useCallback(() => {
    const why = top.why?.length ? `\nWhy:\n- ${top.why.join("\n- ")}` : ""
    const text = `Recommended: ${top.name} (${top.provider})\nScore: ${formatScoreOutOfTen(top.score)}${why}`
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

  const canSendFeedback = !payload.isMock && Boolean(routing?.requestId) && Boolean(top.modelId)
  const handleRating = useCallback(
    (rating: number) => {
      if (!canSendFeedback || !routing?.requestId) return
      if (feedbackState === "submitting") return
      setFeedbackState("submitting")
      void submitModelFeedback({
        modelId: top.modelId,
        rating,
        requestId: routing.requestId,
      }).then(
        () => {
          setFeedbackRating(rating)
          setFeedbackState("success")
        },
        () => {
          setFeedbackState("error")
        },
      )
    },
    [canSendFeedback, feedbackState, routing?.requestId, top.modelId],
  )

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

        {payload.isMock ? (
          <div className="mb-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            <span className="font-semibold">Offline/mock ranking.</span>{" "}
            This is fallback data (not the backend evaluator). Restore API connectivity to see real routing scores.
          </div>
        ) : null}

        {!payload.isMock && providersBanner ? (
          <div
            className={
              providersBanner.tone === "warn"
                ? "mb-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100"
                : "mb-6 rounded-2xl border border-sky-400/30 bg-sky-500/10 px-4 py-3 text-sm text-sky-100"
            }
          >
            <span className="font-semibold">{providersBanner.title}</span>{" "}
            {providersBanner.body}
          </div>
        ) : null}

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
            {truncateText(prompt, 220)}
          </motion.p>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="mt-6 space-y-4"
        >
          <TopModelCard
            top={top}
            routing={routing}
            isMock={Boolean(payload.isMock)}
            canSendFeedback={canSendFeedback}
            feedbackRating={feedbackRating}
            feedbackState={feedbackState}
            onRate={handleRating}
            t={t}
            variants={item}
          />

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
            <details className="group rounded-2xl border border-(--border-subtle) bg-(--surface-glass)/60 p-4 backdrop-blur-sm open:bg-(--surface-glass)/80 sm:p-5">
              <summary className="cursor-pointer list-none text-sm font-semibold text-(--text-muted) [&::-webkit-details-marker]:hidden">
                <span className="inline-flex items-center gap-2">
                  {t("advancedComparisonsTitle")}
                  <span className="text-[11px] font-normal text-(--text-muted) opacity-80 group-open:hidden">
                    — {t("benchmark")}
                  </span>
                </span>
              </summary>
              <div className="mt-4 space-y-5 border-t border-(--border-subtle) pt-4">
                <section className="text-sm leading-relaxed text-(--text-muted)">
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
                </section>
                <BenchmarkChart models={benchmarkModels} />
              </div>
            </details>
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
