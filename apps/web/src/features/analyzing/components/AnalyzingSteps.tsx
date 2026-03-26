import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import { useEffect, useMemo, useRef, useState } from "react"

import { useI18n } from "@/contexts/I18nContext"

import type { TranslationKey } from "@/i18n/translations"

import { StepIndicator } from "./AnalyzingSteps.indicators"
import type { Props, TrailItem } from "./AnalyzingSteps.types"
import { getTrailVisual } from "./AnalyzingSteps.visual"

export function AnalyzingSteps({
  steps,
  activeIndex,
  className,
}: Readonly<Props>) {
  const { t } = useI18n()
  const reduce = useReducedMotion() ?? false

  const maxVisible = 3
  const ids = useRef(0)
  const makeId = () => `trail-${ids.current++}`

  const currentKey = steps[Math.min(activeIndex, steps.length - 1)]?.key

  const initialTrail = useMemo<TrailItem[]>(() => {
    if (!currentKey) return []
    return [{ id: makeId(), key: currentKey, state: "active" }]
  }, [])

  const [trail, setTrail] = useState<TrailItem[]>(initialTrail)
  const prevKeyRef = useRef<TranslationKey | undefined>(currentKey)

  // Update the trail when the current key changes
  useEffect(() => {
    if (!currentKey) return
    const prevKey = prevKeyRef.current
    if (prevKey === currentKey && trail.length) return

    setTrail((prev) => {
      const next = [...prev]
      if (prevKey) {
        const idx = next.findIndex(
          (x) => x.key === prevKey && x.state === "active"
        )
        if (idx >= 0) next[idx] = { ...next[idx], state: "done" }
      }

      next.unshift({ id: makeId(), key: currentKey, state: "active" })

      const trimmed = next.slice(0, maxVisible + 1)
      return trimmed
    })

    prevKeyRef.current = currentKey
    // We intentionally don't include `trail` in deps to avoid re-running for internal reorders.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentKey])

  // Auto-expire items as they drift down (except the top active)
  useEffect(() => {
    if (reduce) return
    if (trail.length <= maxVisible) return
    const id = setTimeout(() => {
      setTrail((prev) => prev.slice(0, maxVisible))
    }, 650)
    return () => clearTimeout(id)
  }, [trail, reduce])

  return (
    <div className={className}>
      <ul className="relative flex w-full justify-center">
        <AnimatePresence initial={false} mode="popLayout">
          {trail.slice(0, maxVisible).map((item, idx) => {
            const visual = getTrailVisual(idx)
            return (
              <motion.li
                key={item.id}
                layout
                initial={
                  reduce
                    ? { opacity: 1 }
                    : { opacity: 0, y: -8, filter: "blur(3px)" }
                }
                animate={{
                  opacity: visual.opacity,
                  y: idx * 28,
                  filter: `blur(${visual.blurPx}px)`,
                }}
                exit={
                  reduce
                    ? { opacity: 0 }
                    : { opacity: 0, y: idx * 28 + 12, filter: "blur(6px)" }
                }
                transition={{
                  duration: reduce ? 0.01 : 0.32,
                  ease: "easeOut",
                }}
                className="absolute left-0 right-0 mx-auto flex w-full max-w-xl items-center justify-center"
              >
                <div className="inline-flex items-center justify-center gap-4">
                  <div className="flex h-6 w-6 items-center justify-center">
                    <StepIndicator state={item.state} reduce={reduce} />
                  </div>
                  <div className="text-[1.55rem] leading-tight font-medium tracking-tight text-(--text-primary) md:text-[1.85rem]">
                    {t(item.key)}
                  </div>
                </div>
              </motion.li>
            )
          })}
        </AnimatePresence>
      </ul>

      {/* Reserve height so the absolute items don't collapse the layout */}
      <div className="h-[140px]" aria-hidden />
    </div>
  )
}
