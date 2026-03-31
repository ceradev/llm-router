import { motion } from "framer-motion"

import { IconCheck } from "@/shared/components"

import type { StepState } from "./AnalyzingSteps.types"

function SpinnerMark({ reduce }: Readonly<{ reduce: boolean }>) {
  return (
    <motion.span
      className="h-5 w-5 rounded-full border-2 border-(--border-subtle) border-t-[#60A5FA]/80 opacity-80"
      animate={reduce ? undefined : { rotate: 360 }}
      transition={
        reduce ? undefined : { duration: 0.9, ease: "linear", repeat: Infinity }
      }
      aria-hidden
    />
  )
}

export function StepIndicator({
  state,
  reduce,
}: Readonly<{ state: StepState; reduce: boolean }>) {
  if (state === "done") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#3B82F6]/10 text-[#93C5FD]">
        <IconCheck className="h-4.5 w-4.5 opacity-80" />
      </span>
    )
  }

  if (state === "active") {
    return (
      <span className="relative flex h-6 w-6 items-center justify-center">
        <span className="absolute inset-0 rounded-full bg-[#60A5FA]/10 blur-[2px]" />
        <SpinnerMark reduce={reduce} />
      </span>
    )
  }

  return (
    <span
      className="h-3.5 w-3.5 rounded-full border-2 border-(--border-subtle) opacity-60"
      aria-hidden
    />
  )
}

