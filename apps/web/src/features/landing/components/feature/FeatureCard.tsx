import type { ReactNode } from "react"
import { motion, useReducedMotion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import type { TranslationKey } from "@/i18n/translations"

type Props = {
  titleKey: TranslationKey
  descriptionKey: TranslationKey
  icon?: ReactNode
}

export function FeatureCard({
  titleKey,
  descriptionKey,
  icon,
}: Readonly<Props>) {
  const { t } = useI18n()
  const reduceMotion = useReducedMotion() ?? false

  return (
    <motion.article
      whileHover={reduceMotion ? undefined : { y: -4 }}
      transition={{ type: "spring", stiffness: 420, damping: 30 }}
      className="group relative overflow-hidden rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-5 backdrop-blur-xl sm:p-6"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
      >
        <div className="absolute -left-12 -top-14 h-40 w-40 rounded-full bg-[#3B82F6]/14 blur-3xl" />
        <div className="absolute -bottom-16 -right-14 h-44 w-44 rounded-full bg-[#0EA5E9]/10 blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0)_45%,rgba(59,130,246,0.10),rgba(14,165,233,0.06))]" />
      </div>

      <div className="relative z-10">
        <div className="flex items-start gap-4">
          {icon ? (
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-[#3B82F6]/25 bg-white/7 text-[#93C5FD] shadow-[0_0_20px_rgba(59,130,246,0.12)]">
              <span className="h-5 w-5">{icon}</span>
            </span>
          ) : null}

          <div className="min-w-0">
            <h3 className="text-base font-semibold tracking-tight text-(--text-primary) sm:text-lg">
              {t(titleKey)}
            </h3>
            <p className="mt-1 text-sm leading-relaxed text-(--text-muted)">
              {t(descriptionKey)}
            </p>
          </div>
        </div>
      </div>

      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-6 bottom-0 h-px bg-linear-to-r from-transparent via-white/14 to-transparent opacity-70"
      />
    </motion.article>
  )
}

