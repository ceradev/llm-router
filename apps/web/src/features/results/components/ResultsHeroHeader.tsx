import { motion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import type { Priority } from "@/features/landing/types"

type ProvidersBanner = {
  tone: "warn" | "info"
  title: string
  body: string
} | null

export function ResultsHeroHeader({
  priority,
  providersBanner,
  containerVariants,
  itemVariants,
}: Readonly<{
  priority: Priority
  providersBanner: ProvidersBanner
  containerVariants: object
  itemVariants: object
}>) {
  const { t } = useI18n()

  return (
    <motion.header
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="mb-8 text-center sm:mb-10"
    >
      <motion.p
        variants={itemVariants}
        className="text-[12px] font-semibold uppercase tracking-wider text-(--text-accent)"
      >
        {t("resultLabel")}
      </motion.p>
      <motion.h1
        variants={itemVariants}
        className="mt-2 text-2xl font-semibold tracking-tight text-(--text-primary) sm:text-3xl"
      >
        {t("resultTitle")}
      </motion.h1>
      <motion.p
        variants={itemVariants}
        className="mx-auto mt-3 max-w-lg text-base leading-relaxed text-(--text-muted)"
      >
        {t("resultBasedOn")}{" "}
        <span className="capitalize text-(--text-primary)">{t(priority)}</span>{" "}
        {t("resultPriority")}
      </motion.p>
      {providersBanner ? (
        <motion.div
          variants={itemVariants}
          className="mx-auto mt-4 max-w-3xl rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-left text-sm text-amber-100"
        >
          <span className="font-semibold">{providersBanner.title}</span>{" "}
          {providersBanner.body}
        </motion.div>
      ) : null}
    </motion.header>
  )
}
