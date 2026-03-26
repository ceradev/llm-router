import { AnimatePresence, motion } from "framer-motion";

import { useI18n } from "@/contexts/I18nContext";
import { hasNonEmptyPrompt } from "@/lib/prompt";
import { AppFooter, IconChevronDown, MainNavbar } from "@/shared/components";
import { heroContainerTransition, heroPromptBlockTransition } from "./config";
import type { Priority, ResponseDepth, UseCaseId } from "./types";
import {
  AdvancedOptionsModal,
  FeaturesSection,
  HeroAnalyseButton,
  HeroHeadline,
  HeroPromptField,
  HowItWorksSection,
  WhySection,
} from "@/features/landing/components";

export type LandingViewProps = {
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
  responseDepth: ResponseDepth;
  setResponseDepth: (d: ResponseDepth) => void;
};

export function LandingView({
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
  responseDepth,
  setResponseDepth,
}: Readonly<LandingViewProps>) {
  const { t } = useI18n();
  const canSubmit = hasNonEmptyPrompt(prompt);
  const scrollToExplanation = () => {
    const target = document.getElementById("how-it-works");
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <motion.div
      className="relative z-10 mx-auto flex min-h-dvh max-w-4xl flex-col px-4 pb-16 pt-6 sm:px-6 sm:pt-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -8 }}
      transition={heroContainerTransition}
    >
      <MainNavbar
        className="mb-5 flex justify-center sm:mb-6"
        onHistoryOpen={onHistoryOpen}
        historyOpen={historyOpen}
      />

      <div className="mb-5 flex justify-center sm:mb-6">
        <p className="flex max-w-176 flex-wrap items-center justify-center gap-x-3 gap-y-2 rounded-full border border-[#3B82F6]/25 bg-[#3B82F6]/10 px-6 py-2.5 text-center">
          <span className="rounded-full border border-[#1D4ED8]/35 bg-[#1D4ED8]/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-[#93C5FD]">
            {t("heroAnnouncementComingSoon")}
          </span>
          <span className="text-[12px] font-semibold leading-relaxed tracking-tight text-(--text-accent) sm:text-sm">
            {t("heroAnnouncementText")}
          </span>
        </p>
      </div>

      <main className="flex min-h-0 flex-1 flex-col justify-start gap-10 overflow-y-auto pt-3 pb-6 sm:gap-12 sm:pt-4 sm:pb-6">
        <HeroHeadline />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={heroPromptBlockTransition}
          className="relative"
        >
          <HeroPromptField prompt={prompt} setPrompt={setPrompt} />

          <div className="mt-5 flex flex-col items-center gap-4 sm:mt-6 sm:flex-row sm:items-center sm:justify-center sm:gap-6">
            <button
              type="button"
              onClick={() => setAdvancedOpen(true)}
              className="rounded-xl px-5 py-3 text-sm font-medium text-(--text-muted) transition-colors hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-subtle) sm:px-6 sm:py-3.5 sm:text-base"
            >
              {t("advancedOptions")}
            </button>
            <HeroAnalyseButton onClick={onAnalyse} canSubmit={canSubmit} />
          </div>

          <div className="mt-4 flex justify-center">
            <motion.button
              type="button"
              aria-label={t("howItWorksTitle")}
              onClick={scrollToExplanation}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: [0, 4, 0] }}
              transition={{
                opacity: { delay: 0.45, duration: 0.35 },
                y: {
                  delay: 0.45,
                  duration: 1.9,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                },
              }}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) shadow-(--shadow-card) transition hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-subtle)"
            >
              <IconChevronDown className="h-5 w-5" />
            </motion.button>
          </div>
        </motion.div>

        <div className="pt-4 sm:pt-8">
          <HowItWorksSection />
          <WhySection />
          <FeaturesSection />
        </div>
      </main>

      <AppFooter className="mt-8 sm:mt-10" />

      <AnimatePresence>
        {advancedOpen ? (
          <AdvancedOptionsModal
            open={advancedOpen}
            onClose={() => setAdvancedOpen(false)}
            onApply={() => setAdvancedOpen(false)}
            priority={priority}
            setPriority={setPriority}
            useCases={useCases}
            toggleUseCase={toggleUseCase}
            providers={providers}
            toggleProvider={toggleProvider}
            responseDepth={responseDepth}
            setResponseDepth={setResponseDepth}
          />
        ) : null}
      </AnimatePresence>
    </motion.div>
  );
}
