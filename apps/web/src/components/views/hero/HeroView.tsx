import { AnimatePresence, motion } from 'framer-motion';
import { hasNonEmptyPrompt } from '../../../lib/prompt';
import {
  AdvancedOptionsPanel,
  type ContextSize,
  type Priority,
  type UseCaseId,
} from '../../panels/AdvancedOptionsPanel';
import { AdvancedRoutingToggle } from './AdvancedRoutingToggle';
import { HeroAnalyseButton } from './HeroAnalyseButton';
import { HeroHeadline } from './HeroHeadline';
import { heroContainerTransition, heroPromptBlockTransition } from './heroMotion';
import { HeroNavbar } from './HeroNavbar';
import { HeroPromptField } from './HeroPromptField';

export type HeroViewProps = {
  prompt: string;
  setPrompt: (v: string) => void;
  advancedOpen: boolean;
  setAdvancedOpen: (v: boolean) => void;
  onAnalyse: () => void;
  onHistoryOpen: () => void;
  historyOpen: boolean;
  priority: Priority;
  setPriority: (p: Priority) => void;
  useCases: Set<UseCaseId>;
  toggleUseCase: (id: UseCaseId) => void;
  providers: Set<string>;
  toggleProvider: (p: string) => void;
  contextSize: ContextSize;
  setContextSize: (c: ContextSize) => void;
};

export function HeroView({
  prompt,
  setPrompt,
  advancedOpen,
  setAdvancedOpen,
  onAnalyse,
  onHistoryOpen,
  historyOpen,
  priority,
  setPriority,
  useCases,
  toggleUseCase,
  providers,
  toggleProvider,
  contextSize,
  setContextSize,
}: Readonly<HeroViewProps>) {
  const canSubmit = hasNonEmptyPrompt(prompt);

  return (
    <motion.div
      className="relative z-10 mx-auto flex min-h-dvh max-w-3xl flex-col px-4 pb-16 pt-6 sm:px-6 sm:pt-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -8 }}
      transition={heroContainerTransition}
    >
      <HeroNavbar onHistoryOpen={onHistoryOpen} historyOpen={historyOpen} />

      <main className="flex min-h-0 flex-1 flex-col justify-center gap-10 overflow-y-auto py-6 sm:gap-12 sm:py-8">
        <HeroHeadline />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={heroPromptBlockTransition}
        >
          <HeroPromptField prompt={prompt} setPrompt={setPrompt} />

          <div className="mt-5 flex flex-col items-center gap-4 sm:mt-6 sm:flex-row sm:items-center sm:justify-center sm:gap-6">
            <AdvancedRoutingToggle advancedOpen={advancedOpen} setAdvancedOpen={setAdvancedOpen} />
            <HeroAnalyseButton onClick={onAnalyse} canSubmit={canSubmit} />
          </div>
        </motion.div>

        <AnimatePresence mode="wait">
          {advancedOpen && (
            <AdvancedOptionsPanel
              priority={priority}
              setPriority={setPriority}
              useCases={useCases}
              toggleUseCase={toggleUseCase}
              providers={providers}
              toggleProvider={toggleProvider}
              contextSize={contextSize}
              setContextSize={setContextSize}
            />
          )}
        </AnimatePresence>
      </main>
    </motion.div>
  );
}
