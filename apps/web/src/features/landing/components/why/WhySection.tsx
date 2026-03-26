import { motion, useReducedMotion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import { InteractiveDemoCard } from "@/features/landing/components/interactive-demo"

export function WhySection() {
  const { t } = useI18n()
  const reduceMotion = useReducedMotion() ?? false

  const drift =
    reduceMotion
      ? undefined
      : {
          y: [0, -10, 0],
          x: [0, 8, 0],
          rotate: [0, 2, 0],
        }

  return (
    <section className="relative mt-12 sm:mt-14">
      <div className="relative overflow-hidden rounded-3xl border border-(--border-subtle) bg-(--surface-glass) backdrop-blur-xl">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(59,130,246,0.18),transparent_55%),radial-gradient(circle_at_80%_40%,rgba(14,165,233,0.16),transparent_58%),radial-gradient(circle_at_50%_120%,rgba(59,130,246,0.10),transparent_55%)]"
        />

        <div className="relative z-10 grid gap-8 p-6 sm:grid-cols-2 sm:items-center sm:gap-10 sm:p-10">
          <div className="min-w-0">
            <p className="inline-flex items-center rounded-full border border-[#3B82F6]/25 bg-[#3B82F6]/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-(--text-accent)">
              {t("whyKicker")}
            </p>
            <h2 className="mt-4 text-2xl font-semibold tracking-tight text-(--text-primary) sm:text-3xl">
              {t("whyTitle")}
            </h2>
            <p className="mt-3 max-w-prose text-sm leading-relaxed text-(--text-muted) sm:text-base">
              {t("whyBody")}
            </p>
          </div>

          <div className="relative min-h-56 overflow-hidden rounded-2xl border border-[#3B82F6]/20 bg-[linear-gradient(135deg,rgba(59,130,246,0.20),rgba(0,0,0,0)_55%,rgba(14,165,233,0.16))] shadow-[0_0_60px_rgba(59,130,246,0.10)] sm:min-h-64">
            <motion.div
              aria-hidden
              animate={drift}
              transition={
                reduceMotion
                  ? { duration: 0 }
                  : { duration: 9, repeat: Infinity, ease: "easeInOut" }
              }
              className="absolute -left-10 -top-10 h-52 w-52 rounded-full bg-[#3B82F6]/26 blur-3xl"
            />
            <motion.div
              aria-hidden
              animate={drift ? { ...drift, x: [0, -10, 0], rotate: [0, -2, 0] } : undefined}
              transition={
                reduceMotion
                  ? { duration: 0 }
                  : { duration: 10.5, repeat: Infinity, ease: "easeInOut" }
              }
              className="absolute -bottom-14 -right-14 h-60 w-60 rounded-full bg-[#0EA5E9]/22 blur-3xl"
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.10),rgba(255,255,255,0)_55%)]"
            />
            <div
              aria-hidden
              className="absolute inset-x-7 top-8 h-px bg-linear-to-r from-transparent via-white/20 to-transparent"
            />
            <div
              aria-hidden
              className="absolute inset-x-10 bottom-10 h-px bg-linear-to-r from-transparent via-white/14 to-transparent"
            />

            <div className="absolute inset-0 z-10 flex items-center justify-center p-2 sm:p-3">
              <InteractiveDemoCard stretch />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

