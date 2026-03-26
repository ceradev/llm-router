import { motion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import {
  analyseButtonSpring,
  analyseHoverWhile,
  analyseShineTransition,
  analyseTapWhile,
} from "@/features/landing/config"

type Props = {
  onClick: () => void
  canSubmit: boolean
}

export function HeroAnalyseButton({ onClick, canSubmit }: Readonly<Props>) {
  const { t } = useI18n()

  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={!canSubmit}
      whileHover={canSubmit ? analyseHoverWhile : undefined}
      whileTap={canSubmit ? analyseTapWhile : undefined}
      transition={analyseButtonSpring}
      className="relative overflow-hidden rounded-xl bg-[linear-gradient(135deg,#3B82F6,#1E40AF)] bg-size-[200%_200%] bg-left px-8 py-3.5 text-sm font-semibold text-white transition-all cursor-pointer duration-50 disabled:cursor-not-allowed disabled:opacity-40 sm:px-10 sm:py-4 sm:text-base"
    >
      <span className="relative z-10">{t("analyse")}</span>

      <motion.span
        className="absolute inset-0 bg-linear-to-r from-white/0 via-white/10 to-white/0"
        initial={{ x: "-100%" }}
        whileHover={canSubmit ? { x: "100%" } : undefined}
        transition={analyseShineTransition}
      />
    </motion.button>
  )
}

