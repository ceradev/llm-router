import { motion, useReducedMotion } from "framer-motion"

import { useTheme } from "@/contexts/ThemeContext"
import LoadingBackground from "./LoadingBackground"
import { ShaderWavesBackground } from "./ShaderWavesBackground"

type Phase = "hero" | "analyzing" | "results"

type Props = {
  phase: Phase
}

export function AppBackgrounds({ phase }: Readonly<Props>) {
  const reduceMotion = useReducedMotion() ?? false
  const { theme } = useTheme()
  const colorScheme = theme === "dark" ? "dark" : "light"

  const t = reduceMotion ? { duration: 0 } : { duration: 0.55, ease: "easeInOut" }
  const showLoading = phase === "analyzing"

  return (
    <div className="absolute inset-0 -z-10" aria-hidden>
      {/* Keep both mounted; only crossfade opacity. */}
      <motion.div
        className="absolute inset-0"
        initial={false}
        animate={{ opacity: showLoading ? 0 : 1 }}
        transition={t}
      >
        <ShaderWavesBackground />
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

