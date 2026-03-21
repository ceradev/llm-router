import { AnimatePresence } from 'framer-motion';
import { useCallback, useState, type ReactNode } from 'react';
import { I18nProvider } from '../contexts/I18nContext';
import { ThemeProvider } from '../contexts/ThemeContext';
import type { ContextSize, Priority, UseCaseId } from './panels/AdvancedOptionsPanel';
import { AnalyzingView } from './views/AnalyzingView';
import { ShaderWavesBackground } from './layout/ShaderWavesBackground';
import { HistoryDrawer, type HistoryItem } from './panels/HistoryDrawer';
import { HeroView } from './views/hero/HeroView';
import { ResultsView } from './results/ResultsView';

type Phase = 'hero' | 'analyzing' | 'results';

export default function LLMRouterApp() {
  const [phase, setPhase] = useState<Phase>('hero');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(true);
  const [prompt, setPrompt] = useState('');

  const [priority, setPriority] = useState<Priority>('quality');
  const [useCases, setUseCases] = useState<Set<UseCaseId>>(() => new Set(['ide', 'api']));
  const [providers, setProviders] = useState<Set<string>>(() => new Set(['OpenAI', 'Anthropic']));
  const [contextSize, setContextSize] = useState<ContextSize>('medium');

  const toggleUseCase = useCallback((id: UseCaseId) => {
    setUseCases((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleProvider = useCallback((p: string) => {
    setProviders((prev) => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p);
      else next.add(p);
      return next;
    });
  }, []);

  const handleAnalyse = useCallback(() => {
    if (!prompt.trim()) return;
    setHistoryOpen(false);
    setPhase('analyzing');
  }, [prompt]);

  const handleAnalyzingComplete = useCallback(() => {
    setPhase('results');
  }, []);

  const handleNewAnalysis = useCallback(() => {
    setPhase('hero');
  }, []);

  const handleStartOver = useCallback(() => {
    setPrompt('');
    setPhase('hero');
  }, []);

  const handleHistoryRerun = useCallback((item: HistoryItem) => {
    setPrompt(item.prompt);
    setHistoryOpen(false);
  }, []);

  const handleHistoryView = useCallback((item: HistoryItem) => {
    setPrompt(item.prompt);
    setAdvancedOpen(true);
    setHistoryOpen(false);
  }, []);

  let phaseView: ReactNode;
  if (phase === 'hero') {
    phaseView = (
      <HeroView
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
        contextSize={contextSize}
        setContextSize={setContextSize}
      />
    );
  } else if (phase === 'analyzing') {
    phaseView = (
      <AnalyzingView
        key="analyzing"
        onComplete={handleAnalyzingComplete}
        onHistoryOpen={() => setHistoryOpen(true)}
        historyOpen={historyOpen}
      />
    );
  } else {
    phaseView = (
      <ResultsView
        key="results"
        prompt={prompt}
        priority={priority}
        onNewAnalysis={handleNewAnalysis}
        onStartOver={handleStartOver}
        onHistoryOpen={() => setHistoryOpen(true)}
        historyOpen={historyOpen}
      />
    );
  }

  return (
    <ThemeProvider>
      <I18nProvider>
        <div className="relative min-h-dvh font-sans antialiased">
          <ShaderWavesBackground />

          <AnimatePresence mode="wait">{phaseView}</AnimatePresence>

          <HistoryDrawer
            open={historyOpen}
            onClose={() => setHistoryOpen(false)}
            onRerun={handleHistoryRerun}
            onView={handleHistoryView}
          />
        </div>
      </I18nProvider>
    </ThemeProvider>
  );
}
