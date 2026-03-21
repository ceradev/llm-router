import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { HistoryTrigger } from '../panels/HistoryDrawer';
import { NavbarToolbar } from '../shell/NavbarControls';

const STEP_KEYS = ['step1', 'step2', 'step3', 'step4'] as const;

type Props = {
  onComplete: () => void;
  onHistoryOpen: () => void;
  historyOpen: boolean;
};

export function AnalyzingView({ onComplete, onHistoryOpen, historyOpen }: Props) {
  const { t } = useI18n();
  const reduce = useReducedMotion();
  const [phaseIndex, setPhaseIndex] = useState(0);

  useEffect(() => {
    if (phaseIndex >= STEP_KEYS.length) {
      const id = setTimeout(onComplete, 1200);
      return () => clearTimeout(id);
    }
    const delay = reduce ? 400 : 1100;
    const id = setTimeout(() => setPhaseIndex((n) => n + 1), delay);
    return () => clearTimeout(id);
  }, [phaseIndex, onComplete, reduce]);

  return (
    <motion.div
      className="relative z-10 flex min-h-dvh flex-col items-center justify-center px-4 py-16"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
    >
      <div className="fixed right-4 top-4 z-20 sm:right-6 sm:top-6">
        <NavbarToolbar
          historySlot={<HistoryTrigger onClick={onHistoryOpen} expanded={historyOpen} />}
        />
      </div>
      <div className="grid w-full max-w-5xl gap-10 lg:grid-cols-[1fr_min(320px,100%)] lg:items-center">
        <motion.div
          className="relative mx-auto flex aspect-square w-full max-w-[min(100%,320px)] items-center justify-center lg:max-w-none"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
        >
          <EnergyOrb reduced={reduce} activeStep={Math.min(phaseIndex, STEP_KEYS.length - 1)} />
        </motion.div>

        <div className="flex flex-col justify-center">
          <h2 className="mb-8 text-center text-xl font-semibold tracking-tight text-[var(--text-primary)] lg:text-left">
            {t('analyzingTitle')}
          </h2>
          <ol className="space-y-4" aria-live="polite">
            {STEP_KEYS.map((key, i) => {
              const done = phaseIndex > i;
              const active = phaseIndex === i && phaseIndex < STEP_KEYS.length;
              const pending = phaseIndex < i;

              return (
                <motion.li
                  key={key}
                  initial={reduce ? false : { opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: reduce ? 0 : 0.08 * i, duration: 0.3 }}
                  className="flex items-start gap-3"
                >
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center">
                    <AnimatePresence mode="wait">
                      {done ? (
                        <motion.span
                          key="done"
                          initial={{ scale: 0.5, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          exit={{ scale: 0.5, opacity: 0 }}
                          className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6] text-xs font-bold text-white shadow-[0_0_20px_rgba(59,130,246,0.35)]"
                        >
                          ✓
                        </motion.span>
                      ) : active ? (
                        <motion.span
                          key="active"
                          className="relative flex h-7 w-7 items-center justify-center"
                          initial={{ scale: 0.9 }}
                          animate={{ scale: 1 }}
                        >
                          <span className="absolute inset-0 rounded-full bg-[#3B82F6]/25 motion-safe:animate-pulse" />
                          <span className="relative h-2.5 w-2.5 rounded-full bg-[#3B82F6] shadow-[0_0_12px_#3B82F6]" />
                        </motion.span>
                      ) : (
                        <motion.span
                          key="pending"
                          className="h-7 w-7 rounded-full border border-[var(--border-subtle)] bg-[var(--surface-glass)]"
                        />
                      )}
                    </AnimatePresence>
                  </span>
                  <span
                    className={
                      pending
                        ? 'text-sm text-[var(--text-muted)] opacity-60'
                        : done
                          ? 'text-sm text-[var(--text-muted)]'
                          : 'text-sm font-medium text-[var(--text-primary)]'
                    }
                  >
                    {t(key)}
                  </span>
                </motion.li>
              );
            })}
          </ol>

          {phaseIndex >= STEP_KEYS.length && (
            <motion.p
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8 text-center text-sm text-[var(--text-accent-tertiary)] lg:text-left"
            >
              {t('analyzingDone')}
            </motion.p>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function EnergyOrb({ reduced, activeStep }: { reduced: boolean; activeStep: number }) {
  const spin = reduced ? 0 : 1;
  return (
    <div className="relative h-full w-full">
      <svg className="h-full w-full overflow-visible" viewBox="0 0 200 200" fill="none" aria-hidden>
        <defs>
          <linearGradient id="orb-line" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.7" />
          </linearGradient>
        </defs>
        <motion.circle
          cx="100"
          cy="100"
          r="72"
          stroke="url(#orb-line)"
          strokeWidth="0.6"
          strokeOpacity="0.35"
          fill="none"
          animate={{ rotate: spin * 360 }}
          transition={{ duration: 28, repeat: Infinity, ease: 'linear' }}
          style={{ transformOrigin: '100px 100px' }}
        />
        <motion.path
          d="M100 28 C 152 52 168 120 100 172 C 32 120 48 52 100 28Z"
          stroke="url(#orb-line)"
          strokeWidth="1.2"
          fill="none"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0.4 }}
          animate={{
            pathLength: 1,
            opacity: [0.35, 0.85, 0.4],
            rotate: spin * -180,
          }}
          transition={{
            pathLength: { duration: 1.8, ease: 'easeInOut' },
            opacity: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
            rotate: { duration: 20, repeat: Infinity, ease: 'linear' },
          }}
          style={{ transformOrigin: '100px 100px' }}
        />
        <motion.path
          d="M40 100 Q100 40 160 100 T100 160"
          stroke="#60A5FA"
          strokeWidth="1"
          fill="none"
          strokeLinecap="round"
          strokeOpacity="0.5"
          animate={{
            d: [
              'M40 100 Q100 40 160 100 T100 160',
              'M40 100 Q100 52 160 100 T92 168',
              'M40 100 Q100 40 160 100 T100 160',
            ],
          }}
          transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        />
      </svg>
      <motion.div
        className="pointer-events-none absolute inset-[18%] rounded-full bg-[radial-gradient(circle,hsla(217,91%,58%,0.12)_0%,transparent_65%)] blur-xl"
        animate={reduced ? undefined : { scale: [1, 1.05, 1], opacity: [0.6, 1, 0.65] }}
        transition={{ duration: 4 + activeStep * 0.4, repeat: Infinity, ease: 'easeInOut' }}
      />
    </div>
  );
}
