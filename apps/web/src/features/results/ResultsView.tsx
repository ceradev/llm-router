import { motion, useReducedMotion } from "framer-motion"
import { useEffect, useMemo, useState } from "react"

import { useI18n } from "@/contexts/I18nContext"
import type { Priority } from "@/features/landing/types"
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
import { useCopyRecommendation } from "./hooks/useCopyRecommendation"
import { useResultFeedback } from "./hooks/useResultFeedback"
import {
  getMockRankedModels,
} from "./utils"
import { CategoryHighlightCard } from "./components/CategoryHighlightCard"
import { FreeAlternativeCard } from "./components/FreeAlternativeCard"
import { ResultsAdvancedComparisons } from "./components/ResultsAdvancedComparisons"
import { ResultsBanners } from "./components/ResultsBanners"
import { ResultsHeroHeader } from "./components/ResultsHeroHeader"
import { ResultsPromptCard } from "./components/ResultsPromptCard"
import { RunnerRow } from "./components/RunnerRow"
import { TopModelCard } from "./components/TopModelCard"
import {
  buildBenchmarkModels,
  buildFallbackPayload,
  buildProvidersBanner,
} from "./utils/resultsView"

const rootFadeTransition = { duration: 0.35 } as const

const staggerContainerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.06 },
  },
}

const staggerItemVariants = {
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

function withFeedbackRating(
  model: ResultsDecisionPayload["topPick"],
  targetModelId: string,
  feedbackRating: number | null,
) {
  if (feedbackRating == null) return model
  if (model.modelId !== targetModelId) return model
  return { ...model, userRating: feedbackRating }
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
  const reduceMotion = useReducedMotion() ?? false
  const [compactMotion, setCompactMotion] = useState(false)

  useEffect(() => {
    const media = globalThis.matchMedia("(max-width: 767px)")
    const update = () => setCompactMotion(media.matches)
    update()
    media.addEventListener("change", update)
    return () => media.removeEventListener("change", update)
  }, [])

  const simplifyMotion = reduceMotion || compactMotion
  const containerVariants = simplifyMotion
    ? {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0, delayChildren: 0 } },
      }
    : staggerContainerVariants
  const itemVariants = simplifyMotion
    ? {
        hidden: { opacity: 0, y: 6 },
        show: { opacity: 1, y: 0, transition: { duration: 0.2 } },
      }
    : staggerItemVariants
  const ranked = getMockRankedModels(priority)

  const fallbackPayload = useMemo(
    () => buildFallbackPayload(priority, ranked),
    [priority, ranked],
  )

  const payload = results ?? fallbackPayload
  const top = payload.topPick
  const routing = payload.routing

  const providersBanner = useMemo(() => buildProvidersBanner(routing), [routing])

  const benchmarkModels = useMemo(() => buildBenchmarkModels(payload), [payload])
  const { copied, handleCopy } = useCopyRecommendation(top)
  const { feedbackRating, feedbackState, handleRating } =
    useResultFeedback({
      isMock: payload.isMock,
      routing,
      top,
    })
  const [hoverRating, setHoverRating] = useState<number | null>(null)
  const selectedRating = hoverRating ?? feedbackRating
  const displayPayload = useMemo<ResultsDecisionPayload>(() => {
    if (feedbackRating == null) return payload
    return {
      ...payload,
      topPick: withFeedbackRating(payload.topPick, top.modelId, feedbackRating),
      freeAlternative: payload.freeAlternative
        ? withFeedbackRating(payload.freeAlternative, top.modelId, feedbackRating)
        : null,
      categoryPicks: payload.categoryPicks.map((pick) => ({
        ...pick,
        model: withFeedbackRating(pick.model, top.modelId, feedbackRating),
      })),
      extraAlternatives: payload.extraAlternatives.map((model) =>
        withFeedbackRating(model, top.modelId, feedbackRating),
      ),
    }
  }, [feedbackRating, payload, top.modelId])

  return (
    <motion.div
      className="relative z-10 mx-auto flex min-h-dvh max-w-4xl flex-col px-4 pb-16 pt-6 sm:px-6 sm:pt-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -10 }}
      transition={rootFadeTransition}
    >
      <div className="flex-1">
        <MainNavbar
          className="mb-8 flex justify-center sm:mb-10"
          onHistoryOpen={onHistoryOpen}
          historyOpen={historyOpen}
        />

        <ResultsBanners
          isMock={Boolean(payload.isMock)}
        />

        <ResultsHeroHeader
          priority={priority}
          providersBanner={providersBanner ?? null}
          containerVariants={containerVariants}
          itemVariants={itemVariants}
        />

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="mt-6 mb-6 flex flex-col items-center"
        >
          <motion.div variants={itemVariants} className="flex items-center gap-1.5">
            {[1, 2, 3, 4, 5].map((value) => {
              const isActive = (selectedRating ?? 0) >= value
              return (
                <button
                  key={value}
                  type="button"
                  disabled={feedbackState === "submitting"}
                  onClick={() => handleRating(value)}
                  onMouseEnter={() => setHoverRating(value)}
                  onMouseLeave={() => setHoverRating(null)}
                  onFocus={() => setHoverRating(value)}
                  onBlur={() => setHoverRating(null)}
                  aria-label={`Rate ${value} out of 5`}
                  className="inline-flex min-h-11 min-w-11 items-center justify-center text-3xl leading-none transition-transform hover:scale-110 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <span
                    className={
                      isActive
                        ? "text-white drop-shadow-[0_0_6px_rgba(255,255,255,0.45)]"
                        : "text-(--text-muted)"
                    }
                    aria-hidden
                  >
                    ★
                  </span>
                </button>
              )
            })}
          </motion.div>
          {feedbackState === "success" ? (
            <motion.p variants={itemVariants} className="mt-2 text-[11px] text-emerald-300">
              Thanks for your feedback.
            </motion.p>
          ) : null}
          {feedbackState === "error" ? (
            <motion.p variants={itemVariants} className="mt-2 text-[11px] text-rose-300">
              Unable to save feedback right now.
            </motion.p>
          ) : null}
        </motion.div>

        <ResultsPromptCard
          prompt={prompt}
          containerVariants={containerVariants}
          itemVariants={itemVariants}
        />

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="mt-6 space-y-6"
        >
          <TopModelCard
            top={top}
            routing={routing}
            isMock={Boolean(payload.isMock)}
            t={t}
            variants={itemVariants}
          />

          {displayPayload.freeAlternative ? (
            <motion.div variants={itemVariants}>
              <FreeAlternativeCard model={displayPayload.freeAlternative} />
            </motion.div>
          ) : null}

          <motion.section variants={itemVariants} className="mt-8 mb-8 sm:mt-12 sm:mb-10 lg:mt-14 lg:mb-12">
            <div className="mb-8 text-center sm:mb-10">
              <p className="text-[12px] font-semibold uppercase tracking-wider text-(--text-accent)">
                {t("alternativesByCategory")}
              </p>
              <h3 className="mt-2 text-xl font-semibold tracking-tight text-(--text-primary) sm:text-2xl">
                {t("otherAlternativesSection")}
              </h3>
              <p className="mx-auto mt-2 max-w-3xl text-sm leading-relaxed text-(--text-muted) sm:text-base">
                {t("rankingOverviewLine")}
              </p>
            </div>
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {displayPayload.categoryPicks.map((pick) => (
                <CategoryHighlightCard key={pick.kind} pick={pick} t={t} />
              ))}
            </div>
          </motion.section>

          <ResultsAdvancedComparisons
            benchmarkModels={benchmarkModels}
            variants={itemVariants}
          />

          {displayPayload.extraAlternatives.length > 0 ? (
            <motion.section variants={itemVariants} className="mt-8 sm:mt-10">
              <div className="mb-8 text-center sm:mb-10">
                <p className="text-[12px] font-semibold uppercase tracking-wider text-(--text-accent)">
                  {t("otherAlternativesSection")}
                </p>
                <h3 className="mt-2 text-xl font-semibold tracking-tight text-(--text-primary) sm:text-2xl">
                  {t("moreModelsTitle")}
                </h3>
                <p className="mx-auto mt-2 max-w-3xl text-sm leading-relaxed text-(--text-muted) sm:text-base">
                  {t("moreModelsSubtitle")}
                </p>
              </div>
              <ul className="space-y-3">
                {displayPayload.extraAlternatives.map((m, i) => (
                  <RunnerRow key={m.id ?? m.name} model={m} index={i} />
                ))}
              </ul>
            </motion.section>
          ) : null}
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-center"
        >
          <motion.button
            variants={itemVariants}
            type="button"
            onClick={handleCopy}
            className="min-h-11 rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-5 py-3 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--surface-glass-hover) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
          >
            {copied ? t("copied") : t("copyRecommendation")}
          </motion.button>
          <motion.button
            variants={itemVariants}
            type="button"
            onClick={onNewAnalysis}
            whileHover={simplifyMotion ? undefined : analyseHoverWhile}
            whileTap={simplifyMotion ? undefined : analyseTapWhile}
            transition={analyseButtonSpring}
            className="relative min-h-11 cursor-pointer overflow-hidden rounded-xl bg-[linear-gradient(135deg,#3B82F6,#1E40AF)] bg-size-[200%_200%] bg-left px-8 py-3.5 text-sm font-semibold text-white transition-all duration-50 disabled:cursor-not-allowed disabled:opacity-40 sm:px-10 sm:py-4 sm:text-base focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
          >
            <span className="relative z-10">{t("newAnalysis")}</span>

            <motion.span
              className="absolute inset-0 bg-linear-to-r from-white/0 via-white/10 to-white/0"
              initial={{ x: "-100%" }}
              whileHover={simplifyMotion ? undefined : { x: "100%" }}
              transition={analyseShineTransition}
            />
          </motion.button>
          <motion.button
            variants={itemVariants}
            type="button"
            onClick={onStartOver}
            className="min-h-11 rounded-xl px-5 py-3 text-sm font-medium text-(--text-muted) transition-colors hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-subtle)"
          >
            {t("startOver")}
          </motion.button>
        </motion.div>
      </div>

      <AppFooter className="mt-8 sm:mt-10" />
    </motion.div>
  )
}
