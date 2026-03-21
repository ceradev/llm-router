import { AnimatePresence, motion } from 'framer-motion';
import { useI18n } from '../../contexts/I18nContext';
import { IconClock } from '../shared/icons';

export type HistoryItem = {
  id: string;
  prompt: string;
  model: string;
  timeAgo: string;
};

const MOCK: HistoryItem[] = [
  { id: '1', prompt: 'Code review for our auth middleware and suggest hardening steps…', model: 'GPT-4', timeAgo: '2h ago' },
  { id: '2', prompt: 'Summarize this quarterly report into 5 bullet points for execs.', model: 'Claude 3.5', timeAgo: 'Yesterday' },
  { id: '3', prompt: 'Draft SQL migrations for adding soft deletes to users.', model: 'Gemini 1.5', timeAgo: '3d ago' },
];

type Props = {
  open: boolean;
  onClose: () => void;
  onRerun?: (item: HistoryItem) => void;
  onView?: (item: HistoryItem) => void;
};

export function HistoryDrawer({ open, onClose, onRerun, onView }: Props) {
  const { t } = useI18n();

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            className="fixed inset-0 z-40 bg-[var(--scrim)] backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            aria-label="Close history"
          />
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="history-title"
            className="fixed right-0 top-0 z-50 flex h-dvh w-[min(100%,380px)] flex-col border-l border-[var(--border-subtle)] bg-[var(--surface-glass)] shadow-[var(--shadow-drawer)] backdrop-blur-xl"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
          >
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-5 py-4">
              <div className="flex items-center gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--surface-glass-hover)] text-[var(--text-accent)]">
                  <IconClock className="h-5 w-5" />
                </span>
                <h2 id="history-title" className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">
                  {t('history')}
                </h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg px-3 py-2 text-sm text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)]"
              >
                {t('close')}
              </button>
            </div>
            <ul className="flex-1 overflow-y-auto p-3">
              {MOCK.map((item, i) => (
                <motion.li
                  key={item.id}
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 * i, duration: 0.25, ease: 'easeOut' }}
                  className="mb-2"
                >
                  <div className="group rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-glass)] p-4 transition-colors hover:border-[var(--surface-glass-hover)] hover:bg-[var(--surface-glass-hover)]">
                    <p className="line-clamp-2 text-sm leading-relaxed text-[var(--text-primary)]">{item.prompt}</p>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
                      <span className="rounded-md bg-[#3B82F6]/15 px-2 py-0.5 font-medium text-[var(--text-accent)]">{item.model}</span>
                      <span>{item.timeAgo}</span>
                    </div>
                    <div className="mt-3 flex gap-2 opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100">
                      <button
                        type="button"
                        className="rounded-lg bg-[var(--surface-glass-hover)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] transition-colors hover:bg-[#3B82F6]/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6]/70"
                        onClick={() => onRerun?.(item)}
                      >
                        {t('rerun')}
                      </button>
                      <button
                        type="button"
                        className="rounded-lg bg-[var(--surface-glass-hover)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] transition-colors hover:bg-[#8B5CF6]/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#8B5CF6]/70"
                        onClick={() => onView?.(item)}
                      >
                        {t('view')}
                      </button>
                    </div>
                  </div>
                </motion.li>
              ))}
            </ul>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

export function HistoryTrigger({ onClick, expanded }: { onClick: () => void; expanded: boolean }) {
  const { t } = useI18n();

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-glass)] text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)] ${
        expanded ? 'bg-[#3B82F6]/15 text-[var(--text-accent)]' : ''
      }`}
      aria-label={t('openHistory')}
      aria-haspopup="dialog"
      aria-expanded={expanded}
    >
      <IconClock className="h-5 w-5" />
    </button>
  );
}
