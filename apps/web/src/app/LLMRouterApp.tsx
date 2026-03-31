import { AnimatePresence } from "framer-motion"
import { useCallback, useEffect, useState } from "react"

import { PhaseView, type Phase } from "@/app/components/PhaseView"
import {
  useRecommendationFlow,
  useRoutingOptionsState,
} from "@/app/hooks"
import { BackgroundMotionProvider } from "@/contexts/BackgroundMotionContext"
import { I18nProvider } from "@/contexts/I18nContext"
import { ThemeProvider } from "@/contexts/ThemeContext"
import { FaqDrawer, FloatingButtons } from "@/features/faq/components"
import { HistoryDrawer } from "@/features/history/components"
import type { HistoryItem } from "@/features/history/types"
import { AppBackgrounds } from "@/shared/components"

export default function LLMRouterApp() {
  const [phase, setPhase] = useState<Phase>("hero")
  const [historyOpen, setHistoryOpen] = useState(false)
  const [faqOpen, setFaqOpen] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [isAtTop, setIsAtTop] = useState(true)
  const [prompt, setPrompt] = useState("")
  const { results, startResultsFetch, restoreResultsFromHistory, abortInFlight } = useRecommendationFlow()
  const {
    priority,
    setPriority,
    useCases,
    toggleUseCase,
    providers,
    toggleProvider,
    responseDepth,
    setResponseDepth,
  } = useRoutingOptionsState()

  const handleHistoryRerun = useCallback((item: HistoryItem) => {
    setPrompt(item.prompt)
    setPhase("hero")
    setAdvancedOpen(false)
    setHistoryOpen(false)
  }, [])

  const handleHistoryView = useCallback((item: HistoryItem) => {
    setPrompt(item.prompt)
    const restored = restoreResultsFromHistory(item.id)
    if (restored) {
      setPhase("results")
      setAdvancedOpen(false)
      setHistoryOpen(false)
      return
    }

    startResultsFetch({
      prompt: item.prompt,
      priority,
      useCases,
      providers,
      responseDepth,
    })
    setPhase("analyzing")
    setHistoryOpen(false)
  }, [priority, providers, responseDepth, restoreResultsFromHistory, startResultsFetch, useCases])

  const handleHistoryOpen = useCallback(() => {
    setHistoryOpen(true)
  }, [])

  const handleFaqOpen = useCallback(() => {
    setFaqOpen(true)
  }, [])

  const handleScrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: "smooth" })
  }, [])

  useEffect(() => {
    const shouldLockScroll = historyOpen || advancedOpen || faqOpen
    if (!shouldLockScroll) return

    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"

    return () => {
      document.body.style.overflow = originalOverflow
    }
  }, [advancedOpen, historyOpen, faqOpen])

  useEffect(() => {
    const handleScroll = () => {
      setIsAtTop(window.scrollY < 100)
    }
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <ThemeProvider>
      <I18nProvider>
        <BackgroundMotionProvider>
          <div className="relative min-h-dvh font-sans antialiased overflow-hidden">
            <AppBackgrounds phase={phase} />

            <AnimatePresence mode="wait">
              <PhaseView
                phase={phase}
                historyOpen={historyOpen}
                onHistoryOpen={handleHistoryOpen}
                hero={{
                  prompt,
                  setPrompt,
                  advancedOpen,
                  setAdvancedOpen,
                  onAnalyse: () => {
                    if (!prompt.trim()) return
                    setHistoryOpen(false)
                    startResultsFetch({
                      prompt,
                      priority,
                      useCases,
                      providers,
                      responseDepth,
                    })
                    setPhase("analyzing")
                  },
                  priority,
                  setPriority,
                  useCases,
                  toggleUseCase,
                  providers,
                  toggleProvider,
                  responseDepth,
                  setResponseDepth,
                }}
                analyzing={{
                  onAnalyzingComplete: () => setPhase("results"),
                }}
                results={{
                  prompt,
                  priority,
                  onNewAnalysis: () => {
                    abortInFlight()
                    setPhase("hero")
                  },
                  onStartOver: () => {
                    abortInFlight()
                    setPrompt("")
                    setPhase("hero")
                  },
                  results,
                }}
              />
            </AnimatePresence>

            <HistoryDrawer
              open={historyOpen}
              onClose={() => setHistoryOpen(false)}
              onRerun={handleHistoryRerun}
              onView={handleHistoryView}
            />

            <FaqDrawer open={faqOpen} onClose={() => setFaqOpen(false)} />

            <FloatingButtons
              onFaqClick={handleFaqOpen}
              onScrollToTop={handleScrollToTop}
              isAtTop={isAtTop}
              hideFaq={phase === "analyzing"}
            />
          </div>
        </BackgroundMotionProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}

