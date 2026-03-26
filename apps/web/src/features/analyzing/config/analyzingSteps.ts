export const ANALYZING_STEP_KEYS = ["step1", "step2", "step3", "step4"] as const

export type AnalyzingStepKey = (typeof ANALYZING_STEP_KEYS)[number]

