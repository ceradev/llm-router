import { AnimatePresence } from "framer-motion"
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"

import { BackgroundMotionProvider } from "@/contexts/BackgroundMotionContext"
import { I18nProvider } from "@/contexts/I18nContext"
import { ThemeProvider } from "@/contexts/ThemeContext"

import type {
  Priority,
  ResponseDepth,
  UseCaseId,
} from "@/features/landing/types/routingOptions"

import { AnalyzingView } from "@/features/analyzing"
import { HistoryDrawer } from "@/features/history/components"
import type { HistoryItem } from "@/features/history/types"
import { LandingView } from "@/features/landing"
import { ResultsView, type ResultsDecisionPayload } from "@/features/results"
import { AppBackgrounds } from "@/shared/components"
import { fetchRecommendation } from "@/shared/api/recommend"

type Phase = "hero" | "analyzing" | "results"

export default function LLMRouterApp() {
  const [phase, setPhase] = useState<Phase>("hero")
  const [historyOpen, setHistoryOpen] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [prompt, setPrompt] = useState("")
  const [results, setResults] = useState<ResultsDecisionPayload | null>(null)
  const resultsAbortRef = useRef<AbortController | null>(null)

  const [priority, setPriority] = useState<Priority>("quality")
  const [useCases, setUseCases] = useState<Set<UseCaseId>>(
    () => new Set(["ide", "api"])
  )
  const [providers, setProviders] = useState<Set<string>>(
    () => new Set(["OpenAI", "Anthropic"])
  )
  const [responseDepth, setResponseDepth] = useState<ResponseDepth>("balanced")

  const toggleUseCase = useCallback((id: UseCaseId) => {
    setUseCases((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  const toggleProvider = useCallback((p: string) => {
    setProviders((prev) => {
      const next = new Set(prev)
      next.has(p) ? next.delete(p) : next.add(p)
      return next
    })
  }, [])

  const startResultsFetch = useCallback(
    (nextPrompt: string, nextPriority: Priority) => {
      resultsAbortRef.current?.abort()
      const controller = new AbortController()
      resultsAbortRef.current = controller

      setResults(null)

      void fetchRecommendation(
        { prompt: nextPrompt, priority: nextPriority },
        { signal: controller.signal }
      ).then(
        (payload) => {
          if (controller.signal.aborted) return
          setResults(payload)
        },
        () => {
          if (controller.signal.aborted) return
          setResults(null)
        }
      )
    },
    []
  )

  const handleAnalyse = useCallback(() => {
    if (!prompt.trim()) return
    setHistoryOpen(false)
    startResultsFetch(prompt, priority)
    setPhase("analyzing")
  }, [prompt, priority, startResultsFetch])

  const handleAnalyzingComplete = useCallback(() => {
    setPhase("results")
  }, [])

  const handleNewAnalysis = useCallback(() => {
    resultsAbortRef.current?.abort()
    setPhase("hero")
  }, [])

  const handleStartOver = useCallback(() => {
    resultsAbortRef.current?.abort()
    setPrompt("")
    setPhase("hero")
  }, [])

  const handleHistoryRerun = useCallback((item: HistoryItem) => {
    setPrompt(item.prompt)
    startResultsFetch(item.prompt, priority)
    setHistoryOpen(false)
  }, [priority, startResultsFetch])

  const handleHistoryView = useCallback((item: HistoryItem) => {
    setPrompt(item.prompt)
    setAdvancedOpen(true)
    startResultsFetch(item.prompt, priority)
    setHistoryOpen(false)
  }, [priority, startResultsFetch])

  useEffect(() => {
    return () => {
      resultsAbortRef.current?.abort()
    }
  }, [])

  let phaseView: ReactNode

  if (phase === "hero") {
    phaseView = (
      <LandingView
        key="hero"
        prompt={prompt}
        setPrompt={setPrompt}
        advancedOpen={advancedOpen}
        setAdvancedOpen={setAdvancedOpen}
        onAnalyse={handleAnalyse}
        onHistoryOpen={() => setHistoryOpen(true)}
        historyOpen={historyOpen}
        priority={priority}
        setPriority={setPriority}
        useCases={useCases}
        toggleUseCase={toggleUseCase}
        providers={providers}
        toggleProvider={toggleProvider}
        responseDepth={responseDepth}
        setResponseDepth={setResponseDepth}
      />
    )
  } else if (phase === "analyzing") {
    phaseView = (
      <AnalyzingView
        key="analyzing"
        onComplete={handleAnalyzingComplete}
        onHistoryOpen={() => setHistoryOpen(true)}
        historyOpen={historyOpen}
      />
    )
  } else {
    phaseView = (
      <ResultsView
        key="results"
        prompt={prompt}
        priority={priority}
        results={results ?? undefined}
        onNewAnalysis={handleNewAnalysis}
        onStartOver={handleStartOver}
        onHistoryOpen={() => setHistoryOpen(true)}
        historyOpen={historyOpen}
      />
    )
  }

  return (
    <ThemeProvider>
      <I18nProvider>
        <BackgroundMotionProvider>
          <div className="relative min-h-dvh font-sans antialiased overflow-hidden">
            <AppBackgrounds phase={phase} />

            <AnimatePresence mode="wait">{phaseView}</AnimatePresence>

            <HistoryDrawer
              open={historyOpen}
              onClose={() => setHistoryOpen(false)}
              onRerun={handleHistoryRerun}
              onView={handleHistoryView}
            />
          </div>
        </BackgroundMotionProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}

