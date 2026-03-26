import { AnimatePresence, motion, useReducedMotion } from "framer-motion"

import { useDemoFlow } from "@/features/landing/hooks"

import { DemoInput } from "./DemoInput"
import { DemoLoading } from "./DemoLoading"
import { DemoResult } from "./DemoResult"

const TIMINGS_MS = {
  input: 2200,
  loading: 4200,
  result: 6500,
} as const

type InteractiveDemoCardProps = {
  stretch?: boolean
}

export function InteractiveDemoCard({
  stretch = false,
}: Readonly<InteractiveDemoCardProps>) {
  const reduceMotion = useReducedMotion() ?? false
  const { phase } = useDemoFlow({ enabled: true, initialPhase: "input", timingsMs: TIMINGS_MS })

  const transition = {
    duration: reduceMotion ? 0 : 0.35,
    ease: "easeOut",
  } as const

  const phaseKey = phase

  let demoContent: React.ReactNode
  switch (phase) {
    case "input":
      demoContent = <DemoInput prompt="Build a SaaS with AI" stretch={stretch} />
      break
    case "loading":
      demoContent = <DemoLoading text="Analyzing..." stretch={stretch} />
      break
    case "result":
      demoContent = (
        <DemoResult
          modelName="Claude 3.5 Sonnet"
          description="Strong planning and reliable reasoning for production-ready workflows."
          matchScore={96}
          stretch={stretch}
        />
      )
      break
  }

  return (
    <div className={stretch ? "relative h-full w-full" : "relative"}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={phaseKey}
          className={stretch ? "h-full w-full" : undefined}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={transition}
        >
          {demoContent}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

export function InteractiveDemo() {
  return (
    <section className="mt-8 sm:mt-10">
      <div className="grid gap-8 md:grid-cols-2 md:items-start">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-(--text-primary)">
            See how it works
          </h2>
          <p className="mt-3 max-w-prose text-sm leading-relaxed text-(--text-muted)">
            A quick, auto-playing preview of the routing loop: prompt in, analysis in motion, and a
            top match out.
          </p>
        </div>

        <InteractiveDemoCard />
      </div>
    </section>
  )
}

