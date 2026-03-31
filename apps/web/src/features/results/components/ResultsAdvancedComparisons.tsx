import { motion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import type { ModelDecision } from "@/features/results/types"
import { BenchmarkChart } from "./BenchmarkChart"

export function ResultsAdvancedComparisons({
  benchmarkModels,
  variants,
}: Readonly<{
  benchmarkModels: ModelDecision[]
  variants: object
}>) {
  const { t } = useI18n()

  return (
    <motion.div variants={variants}>
      <section className="mt-8 mb-8 sm:mt-10 sm:mb-10 lg:mt-12 lg:mb-12">
        <p className="text-[12px] font-semibold uppercase tracking-wider text-(--text-accent) text-center">
          {t("advancedComparisonsTitle")}
        </p>
        <h3 className="mt-2 text-center text-xl font-semibold tracking-tight text-(--text-primary) sm:text-2xl">
          {t("benchmarkTitle")}
        </h3>
        <p className="mx-auto mt-2 mb-8 max-w-3xl text-center text-sm leading-relaxed text-(--text-muted) sm:mb-10 sm:text-base">
          {t("benchmarkSubtitle")}
        </p>
        <BenchmarkChart models={benchmarkModels} showHeader={false} />
      </section>
    </motion.div>
  )
}
