import type { TranslationKey } from "@/i18n/translations"

export type Step = {
  key: TranslationKey
}

export type StepState = "done" | "active" | "pending"

export type Props = {
  steps: Step[]
  activeIndex: number
  className?: string
}

export type TrailItem = {
  id: string
  key: TranslationKey
  state: StepState
}

