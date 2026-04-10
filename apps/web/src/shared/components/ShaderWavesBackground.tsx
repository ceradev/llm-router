import React, { useMemo } from "react"
import { useReducedMotion } from "framer-motion"
import { useBackgroundMotion } from "@/contexts/BackgroundMotionContext"
import { useTheme } from "@/contexts/ThemeContext"

const ShaderWavesScene = React.lazy(() =>
  import("./ShaderWavesScene").then((m) => ({ default: m.ShaderWavesScene }))
)

type Props = {
  active?: boolean
}

export function ShaderWavesBackground({ active = true }: Readonly<Props>) {
  const reduce = useReducedMotion() ?? false
  const { theme } = useTheme()
  const { enabled } = useBackgroundMotion()
  const colorScheme = theme === "dark" ? "dark" : "light"

  const isDisabled = !active || reduce || !enabled
  const animate: "off" | "on" = isDisabled ? "off" : "on"
  
  const lightOverlayClass = useMemo(
    () => (colorScheme === "light" ? "bg-white/16" : "bg-transparent"),
    [colorScheme]
  )

  const sceneProps = useMemo(
    () => ({ animate, colorScheme }),
    [animate, colorScheme]
  )

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-(--bg-base)"
      aria-hidden
    >
      <React.Suspense fallback={null}>
        <ShaderWavesScene {...sceneProps} />
      </React.Suspense>
      <div className={`absolute inset-0 ${lightOverlayClass}`} />
    </div>
  )
}

