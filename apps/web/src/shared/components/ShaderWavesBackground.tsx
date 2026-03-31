import { useReducedMotion } from "framer-motion"
import { lazy, Suspense } from "react"

import { useBackgroundMotion } from "@/contexts/BackgroundMotionContext"
import { useTheme } from "@/contexts/ThemeContext"

const ShaderWavesScene = lazy(() =>
  import("./ShaderWavesScene").then((m) => ({ default: m.ShaderWavesScene }))
)

type Props = {
  /**
   * When false, the WebGL shader is kept mounted but animation is paused
   * to avoid unnecessary GPU/CPU work while hidden behind other scenes.
   */
  active?: boolean
}

export function ShaderWavesBackground({ active = true }: Readonly<Props>) {
  const reduce = useReducedMotion() ?? false
  const { theme } = useTheme()
  const { enabled } = useBackgroundMotion()
  const colorScheme = theme === "dark" ? "dark" : "light"

  const animate: "off" | "on" = !active || reduce || !enabled ? "off" : "on"
  const lightOverlayClass =
    // `backdrop-blur` on a fixed fullscreen layer is a common scroll-jank culprit on Chrome.
    // Keep a light veil without blur to reduce repaints.
    colorScheme === "light" ? "bg-white/16" : "bg-transparent"

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-(--bg-base)"
      aria-hidden
    >
      <Suspense fallback={null}>
        <ShaderWavesScene animate={animate} colorScheme={colorScheme} />
      </Suspense>
      <div className={`absolute inset-0 ${lightOverlayClass}`} />
    </div>
  )
}

