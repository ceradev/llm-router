import { motion } from 'framer-motion';
import { useCallback, useState } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import type { Priority } from '../panels/AdvancedOptionsPanel';
import { HistoryTrigger } from '../panels/HistoryDrawer';
import { NavbarToolbar } from '../shell/NavbarControls';
import { formatLatency, getMockRankedModels, type RankedModel } from './results';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.06 },
  },
};

const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] } },
};

type Props = {
  prompt: string;
  priority: Priority;
  onNewAnalysis: () => void;
  onStartOver: () => void;
  onHistoryOpen: () => void;
  historyOpen: boolean;
};

function truncate(s: string, max: number) {
  const t = s.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

export function ResultsView({
  prompt,
  priority,
  onNewAnalysis,
  onStartOver,
  onHistoryOpen,
  historyOpen,
}: Props) {
  const { t } = useI18n();
  const ranked = getMockRankedModels(priority);
  const top = ranked[0];
  const runners = ranked.slice(1);
  const [copied, setCopied] = useState(false);

  const getCostLabel = (rel: RankedModel['costRel']) =>
    rel === 'low' ? t('lowerCost') : rel === 'medium' ? t('moderateCost') : t('higherCost');

  const handleCopy = useCallback(() => {
    const text = `Recommended: ${top.name} (${top.provider})\n${top.note}`;
    void navigator.clipboard.writeText(text).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => {
        setCopied(false);
      },
    );
  }, [top]);

  return (
    <motion.div
      className="relative z-10 mx-auto min-h-dvh max-w-2xl px-4 pb-16 pt-6 sm:px-6 sm:pt-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.35 }}
    >
      <div className="fixed right-4 top-4 z-20 sm:right-6 sm:top-6">
        <NavbarToolbar
          historySlot={<HistoryTrigger onClick={onHistoryOpen} expanded={historyOpen} />}
        />
      </div>

      <motion.header
        variants={container}
        initial="hidden"
        animate="show"
        className="mb-8 text-center sm:mb-10"
      >
        <motion.p variants={item} className="text-xs font-semibold uppercase tracking-wider text-[var(--text-accent)]">
          {t('resultLabel')}
        </motion.p>
        <motion.h1 variants={item} className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-3xl">
          {t('resultTitle')}
        </motion.h1>
        <motion.p variants={item} className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-[var(--text-muted)]">
          {t('resultBasedOn')} <span className="capitalize text-[var(--text-primary)]">{t(priority)}</span> {t('resultPriority')}
        </motion.p>
      </motion.header>

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-glass)] p-4 shadow-[var(--shadow-elevated)] backdrop-blur-xl sm:p-5"
      >
        <motion.p variants={item} className="text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
          {t('yourPrompt')}
        </motion.p>
        <motion.p variants={item} className="mt-1.5 text-sm leading-relaxed text-[var(--text-primary)]">
          {truncate(prompt, 220)}
        </motion.p>
      </motion.div>

      <motion.div variants={container} initial="hidden" animate="show" className="mt-6 space-y-4">
        <motion.div
          variants={item}
          className="relative overflow-hidden rounded-2xl border border-[#3B82F6]/30 bg-gradient-to-br from-[#3B82F6]/15 via-[var(--surface-glass)] to-[#8B5CF6]/10 p-5 shadow-[0_0_40px_rgba(59,130,246,0.12)] backdrop-blur-xl sm:p-6"
        >
          <div className="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-[#8B5CF6]/20 blur-2xl" aria-hidden />
          <div className="relative">
            <span className="inline-flex items-center rounded-full bg-[var(--badge-bg)] px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-accent-secondary)]">
              {t('topPick')}
            </span>
            <h2 className="mt-3 text-xl font-semibold text-[var(--text-primary)] sm:text-2xl">{top.name}</h2>
            <p className="mt-1 text-sm text-[var(--text-accent)]">{top.provider}</p>
            <p className="mt-4 text-sm leading-relaxed text-[var(--text-muted)]">{top.note}</p>
            <dl className="mt-5 grid grid-cols-3 gap-3 border-t border-[var(--border-subtle)] pt-5 text-center sm:gap-4">
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-[var(--text-muted)]">{t('match')}</dt>
                <dd className="mt-1 text-lg font-semibold tabular-nums text-[var(--text-primary)]">{top.score}%</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-[var(--text-muted)]">{t('latency')}</dt>
                <dd className="mt-1 text-sm font-medium tabular-nums text-[var(--text-primary)]">{formatLatency(top.latencyMs)}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-[var(--text-muted)]">{t('costLabel')}</dt>
                <dd className="mt-1 text-sm font-medium text-[var(--text-primary)]">{getCostLabel(top.costRel)}</dd>
              </div>
            </dl>
          </div>
        </motion.div>

        {runners.length > 0 && (
          <motion.div variants={item}>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">{t('runnersUp')}</p>
            <ul className="space-y-2">
              {runners.map((m, i) => (
                <RunnerRow key={m.name} model={m} index={i} />
              ))}
            </ul>
          </motion.div>
        )}
      </motion.div>

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-center"
      >
        <motion.button
          variants={item}
          type="button"
          onClick={handleCopy}
          className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-glass)] px-5 py-3 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-glass-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)]"
        >
          {copied ? t('copied') : t('copyRecommendation')}
        </motion.button>
        <motion.button
          variants={item}
          type="button"
          onClick={onNewAnalysis}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          transition={{ type: 'spring', stiffness: 400, damping: 22 }}
          className="rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] px-6 py-3 text-sm font-semibold text-white shadow-[0_12px_40px_rgba(59,130,246,0.25)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)]"
        >
          {t('newAnalysis')}
        </motion.button>
        <motion.button
          variants={item}
          type="button"
          onClick={onStartOver}
          className="rounded-xl px-5 py-3 text-sm font-medium text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-subtle)]"
        >
          {t('startOver')}
        </motion.button>
      </motion.div>
    </motion.div>
  );
}

function RunnerRow({ model, index }: { model: RankedModel; index: number }) {
  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.12 + index * 0.06, duration: 0.3 }}
      className="flex items-center justify-between gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-glass)] px-4 py-3 backdrop-blur-sm transition-colors hover:border-[var(--surface-glass-hover)] hover:bg-[var(--surface-glass-hover)]"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-[var(--text-primary)]">{model.name}</p>
        <p className="text-xs text-[var(--text-muted)]">{model.provider}</p>
      </div>
      <div className="shrink-0 text-right">
        <p className="text-sm font-semibold tabular-nums text-[var(--text-primary)]">{model.score}%</p>
        <p className="text-[11px] text-[var(--text-muted)]">{formatLatency(model.latencyMs)}</p>
      </div>
    </motion.li>
  );
}
