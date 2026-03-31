import { motion } from "framer-motion"
import { useMemo, useState } from "react"

import { useI18n } from "@/contexts/I18nContext"
import { truncateText } from "@/features/results/utils/resultsView"

export function ResultsPromptCard({
  prompt,
  containerVariants,
  itemVariants,
}: Readonly<{
  prompt: string
  containerVariants: object
  itemVariants: object
}>) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(false)
  const shouldCollapse = useMemo(() => prompt.trim().length > 220, [prompt])
  const displayedPrompt = shouldCollapse && !expanded ? truncateText(prompt, 220) : prompt

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-elevated) backdrop-blur-xl sm:p-5"
    >
      <motion.p
        variants={itemVariants}
        className="text-[12px] font-medium uppercase tracking-wide text-(--text-muted)"
      >
        {t("yourPrompt")}
      </motion.p>
      <motion.p
        variants={itemVariants}
        className={
          expanded
            ? "mt-1.5 max-h-52 overflow-y-auto pr-1 text-base leading-relaxed text-(--text-primary)"
            : "mt-1.5 text-base leading-relaxed text-(--text-primary)"
        }
      >
        {displayedPrompt}
      </motion.p>
      {shouldCollapse ? (
        <motion.div variants={itemVariants} className="mt-2">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="min-h-11 rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wide text-(--text-accent) transition-colors hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
            aria-expanded={expanded}
          >
            {expanded ? t("showLess") : t("showMore")}
          </button>
        </motion.div>
      ) : null}
    </motion.div>
  )
}
