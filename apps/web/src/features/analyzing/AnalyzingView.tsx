import { motion, useReducedMotion } from "framer-motion"

import { AnalyzingSteps, TypingAI } from "./components"
import { useAnalyzingProgress } from "./hooks"

type Props = {
  onComplete: () => void
  onHistoryOpen: () => void
  historyOpen: boolean
}

export function AnalyzingView({
  onComplete,
}: Readonly<Props>) {
  const reduceMotion = useReducedMotion() ?? false

  const { steps, activeStepIndex } = useAnalyzingProgress({
    reduceMotion,
    onComplete,
  })

  return (
    <motion.div
      className="relative min-h-dvh flex flex-col"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Center Scene */}
      <div className="flex flex-1 flex-col items-center justify-center px-5 py-10">
        <div className="w-full max-w-xl">
          <div className="flex flex-col items-center">
            <TypingAI color="#3B82F6" />

            <div className="mt-16 w-full">
              <AnalyzingSteps steps={steps} activeIndex={activeStepIndex} />
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

