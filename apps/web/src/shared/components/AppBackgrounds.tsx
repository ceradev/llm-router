import { motion, useReducedMotion } from "framer-motion"
import { useEffect, useState } from "react"

import { useBackgroundMotion } from "@/contexts/BackgroundMotionContext"
import { useTheme } from "@/contexts/ThemeContext"
import LoadingBackground from "./LoadingBackground"
import { ShaderWavesBackground } from "./ShaderWavesBackground"

type Phase = "hero" | "analyzing" | "results"

type Props = {
  phase: Phase
}

export function AppBackgrounds({ phase }: Readonly<Props>) {
  const reduceMotion = useReducedMotion() ?? false
  const { hasExplicitPreference } = useBackgroundMotion()
  const { theme } = useTheme()
  const [mobileViewport, setMobileViewport] = useState(false)
  const [lowEndMobile, setLowEndMobile] = useState(false)
  const colorScheme = theme === "dark" ? "dark" : "light"

  const t = reduceMotion ? { duration: 0 } : { duration: 0.55, ease: "easeInOut" }
  const showLoading = phase === "analyzing"
  const lowEndFallbackApplies = lowEndMobile && !hasExplicitPreference
  const useStaticBackground = reduceMotion || lowEndFallbackApplies

  useEffect(() => {
    const media = globalThis.matchMedia("(max-width: 767px)")
    const update = () => setMobileViewport(media.matches)
    update()
    media.addEventListener("change", update)
    return () => media.removeEventListener("change", update)
  }, [])

  useEffect(() => {
    if (!mobileViewport) {
      setLowEndMobile(false)
      return
    }

    const navigatorInfo = globalThis.navigator
    const hardwareThreads = navigatorInfo.hardwareConcurrency
    const memoryGb = navigatorInfo.deviceMemory
    const saveData = Boolean(navigatorInfo.connection?.saveData)

    const weakCpu = typeof hardwareThreads === "number" && hardwareThreads <= 4
    const lowMemory = typeof memoryGb === "number" && memoryGb <= 4
    setLowEndMobile(weakCpu || lowMemory || saveData)
  }, [mobileViewport])

  return (
    <div className="absolute inset-0 -z-10" aria-hidden>
      {/* Keep both mounted; only crossfade opacity. */}
      <motion.div
        className="absolute inset-0"
        initial={false}
        animate={{ opacity: showLoading ? 0 : 1 }}
        transition={t}
      >
        {useStaticBackground ? (
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(59,130,246,0.22)_0%,rgba(59,130,246,0)_40%),radial-gradient(circle_at_82%_14%,rgba(14,165,233,0.18)_0%,rgba(14,165,233,0)_38%),linear-gradient(180deg,var(--bg-canvas)_0%,var(--bg-canvas-alt)_100%)]" />
        ) : (
          <ShaderWavesBackground active={!showLoading} />
        )}
      </motion.div>

      <motion.div
        className="absolute inset-0"
        initial={false}
        animate={{ opacity: showLoading ? 1 : 0 }}
        transition={t}
        style={{ pointerEvents: "none" }}
      >
        <LoadingBackground colorScheme={colorScheme} />
      </motion.div>
    </div>
  )
}

