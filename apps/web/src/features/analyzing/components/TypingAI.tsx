import { motion, useReducedMotion } from "framer-motion"

type Props = {
  color: string
}

function clamp01(n: number) {
  return Math.min(1, Math.max(0, n))
}

function hexToRgba(hex: string, alpha: number) {
  const raw = hex.trim().replace(/^#/, "")
  const a = clamp01(alpha)

  if (raw.length === 3) {
    const r = Number.parseInt(raw[0] + raw[0], 16)
    const g = Number.parseInt(raw[1] + raw[1], 16)
    const b = Number.parseInt(raw[2] + raw[2], 16)
    return `rgba(${r}, ${g}, ${b}, ${a})`
  }

  if (raw.length === 6) {
    const r = Number.parseInt(raw.slice(0, 2), 16)
    const g = Number.parseInt(raw.slice(2, 4), 16)
    const b = Number.parseInt(raw.slice(4, 6), 16)
    return `rgba(${r}, ${g}, ${b}, ${a})`
  }

  return null
}

function glowShadow(color: string, alpha: number, radiusPx: number) {
  const rgba = color.startsWith("#") ? hexToRgba(color, alpha) : null
  const glow = rgba ?? color
  return `0 0 ${radiusPx}px ${glow}`
}

const DOTS = [0, 1, 2] as const

export function TypingAI({ color }: Readonly<Props>) {
  const reduce = useReducedMotion() ?? false

  const dotBaseClass =
    "h-6 w-6 md:h-12 md:w-12 rounded-full will-change-transform"
  const gapClass = "gap-5 md:gap-6"
  const containerClass =
    "w-full max-w-sm md:max-w-md h-16 md:h-20 inline-flex items-center justify-center"

  if (reduce) {
    return (
      <div className={`${containerClass} ${gapClass}`} aria-hidden>
        {DOTS.map((i) => (
          <span
            key={i}
            className={dotBaseClass}
            style={{
              backgroundColor: color,
              boxShadow: glowShadow(color, 0.55, 22),
              opacity: 0.85,
            }}
          />
        ))}
      </div>
    )
  }

  const lift = 10
  const ease = [0.55, 0.08, 0.35, 1] as const

  return (
    <div className={`${containerClass} ${gapClass}`} aria-hidden>
      {DOTS.map((i) => {
        // Subtle, intentional variance so it never feels robotic.
        const delay = 0.18 * i + (i === 1 ? 0.03 : 0)
        const durationMap: Record<number, number> = { 0: 1.38, 1: 1.45, 2: 1.52 }
        const duration = durationMap[i] ?? 1.45

        return (
          <motion.span
            key={i}
            className={dotBaseClass}
            animate={{
              y: [0, -lift, 0],
              scale: [1, 1.18, 1],
              opacity: [0.55, 0.98, 0.6],
              backgroundColor: color,
              boxShadow: [
                glowShadow(color, 0.35, 18),
                glowShadow(color, 0.8, 26),
                glowShadow(color, 0.4, 18),
              ],
            }}
            transition={{
              y: { duration, ease, repeat: Infinity, delay },
              scale: { duration, ease, repeat: Infinity, delay },
              opacity: { duration, ease, repeat: Infinity, delay },
              boxShadow: { duration, ease, repeat: Infinity, delay },
              backgroundColor: { duration: 0.55, ease: "easeInOut" },
            }}
          />
        )
      })}
    </div>
  )
}

