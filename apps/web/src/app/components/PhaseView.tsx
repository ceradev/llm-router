import type { ReactNode } from "react"

import { AnalyzingView } from "@/features/analyzing"
import { LandingView } from "@/features/landing"
import { ResultsView, type ResultsDecisionPayload } from "@/features/results"
import type {
  Priority,
  ResponseDepth,
  UseCaseId,
} from "@/features/landing/types/routingOptions"

export type Phase = "hero" | "analyzing" | "results"

type HeroPhaseProps = {
  prompt: string
  setPrompt: (value: string) => void
  advancedOpen: boolean
  setAdvancedOpen: (value: boolean) => void
  onAnalyse: () => void
  priority: Priority
  setPriority: (value: Priority) => void
  useCases: Set<UseCaseId>
  toggleUseCase: (id: UseCaseId) => void
  providers: Set<string>
  toggleProvider: (provider: string) => void
  responseDepth: ResponseDepth
  setResponseDepth: (value: ResponseDepth) => void
}

type AnalyzingPhaseProps = {
  onAnalyzingComplete: () => void
}

type ResultsPhaseProps = {
  prompt: string
  priority: Priority
  onNewAnalysis: () => void
  onStartOver: () => void
  results: ResultsDecisionPayload | null
}

type Props = {
  phase: Phase
  historyOpen: boolean
  onHistoryOpen: () => void
  hero: HeroPhaseProps
  analyzing: AnalyzingPhaseProps
  results: ResultsPhaseProps
}

export function PhaseView({
  phase,
  historyOpen,
  onHistoryOpen,
  hero,
  analyzing,
  results,
}: Readonly<Props>) {
  let phaseView: ReactNode

  if (phase === "hero") {
    phaseView = (
      <LandingView
        key="hero"
        prompt={hero.prompt}
        setPrompt={hero.setPrompt}
        advancedOpen={hero.advancedOpen}
        setAdvancedOpen={hero.setAdvancedOpen}
        onAnalyse={hero.onAnalyse}
        onHistoryOpen={onHistoryOpen}
        historyOpen={historyOpen}
        priority={hero.priority}
        setPriority={hero.setPriority}
        useCases={hero.useCases}
        toggleUseCase={hero.toggleUseCase}
        providers={hero.providers}
        toggleProvider={hero.toggleProvider}
        responseDepth={hero.responseDepth}
        setResponseDepth={hero.setResponseDepth}
      />
    )
  } else if (phase === "analyzing") {
    phaseView = (
      <AnalyzingView
        key="analyzing"
        onComplete={analyzing.onAnalyzingComplete}
        onHistoryOpen={onHistoryOpen}
        historyOpen={historyOpen}
      />
    )
  } else {
    phaseView = (
      <ResultsView
        key="results"
        prompt={results.prompt}
        priority={results.priority}
        results={results.results ?? undefined}
        onNewAnalysis={results.onNewAnalysis}
        onStartOver={results.onStartOver}
        onHistoryOpen={onHistoryOpen}
        historyOpen={historyOpen}
      />
    )
  }

  return phaseView
}
