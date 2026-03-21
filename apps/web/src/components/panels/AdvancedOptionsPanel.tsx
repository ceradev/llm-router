import { motion } from 'framer-motion';
import { useI18n } from '../../contexts/I18nContext';
import type { TranslationKey } from '../../i18n/translations';
import { cn } from '../../lib/cn';
import { IconApi, IconBatch, IconChat, IconCode, IconInfo } from '../shared/icons';

export type Priority = 'quality' | 'speed' | 'cost';
export type UseCaseId = 'ide' | 'api' | 'chatbot' | 'batch';
export type ContextSize = 'small' | 'medium' | 'large';

const USE_CASE_IDS: { id: UseCaseId; titleKey: string; blurbKey: string; Icon: typeof IconCode }[] = [
  { id: 'ide', titleKey: 'useCaseIde', blurbKey: 'useCaseIdeBlurb', Icon: IconCode },
  { id: 'api', titleKey: 'useCaseApi', blurbKey: 'useCaseApiBlurb', Icon: IconApi },
  { id: 'chatbot', titleKey: 'useCaseChatbot', blurbKey: 'useCaseChatbotBlurb', Icon: IconChat },
  { id: 'batch', titleKey: 'useCaseBatch', blurbKey: 'useCaseBatchBlurb', Icon: IconBatch },
];

const PROVIDERS = ['OpenAI', 'Anthropic', 'Google'] as const;

const CONTEXT_KEYS: Record<ContextSize, string> = {
  small: 'contextSmall',
  medium: 'contextMedium',
  large: 'contextLarge',
};

type Props = {
  priority: Priority;
  setPriority: (p: Priority) => void;
  useCases: Set<UseCaseId>;
  toggleUseCase: (id: UseCaseId) => void;
  providers: Set<string>;
  toggleProvider: (p: string) => void;
  contextSize: ContextSize;
  setContextSize: (c: ContextSize) => void;
};

function SectionLabel({ children, hint }: { children: string; hint: string }) {
  return (
    <div className="mb-2 flex items-center gap-1.5">
      <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">{children}</span>
      <span className="group relative inline-flex">
        <button
          type="button"
          className="rounded p-0.5 text-[var(--text-muted)] opacity-60 transition-colors hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)]"
          aria-label={hint}
        >
          <IconInfo className="h-3.5 w-3.5" />
        </button>
        <span className="pointer-events-none absolute left-1/2 top-full z-10 mt-1 w-48 -translate-x-1/2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)]/95 px-2 py-1.5 text-[11px] leading-snug text-[var(--text-primary)] opacity-0 shadow-lg backdrop-blur-md transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
          {hint}
        </span>
      </span>
    </div>
  );
}

export function AdvancedOptionsPanel({
  priority,
  setPriority,
  useCases,
  toggleUseCase,
  providers,
  toggleProvider,
  contextSize,
  setContextSize,
}: Props) {
  const { t } = useI18n();
  const priorities: Priority[] = ['quality', 'speed', 'cost'];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
      className="mt-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-glass)] p-5 shadow-[var(--shadow-elevated)] backdrop-blur-xl sm:p-6"
    >
      <div className="mb-6">
        <SectionLabel hint={t('priorityHint')}>{t('priority')}</SectionLabel>
        <div
          className="inline-flex rounded-full border border-[var(--border-subtle)] bg-[var(--segment-bg)] p-1"
          role="tablist"
          aria-label="Routing priority"
        >
          {priorities.map((p) => (
            <button
              key={p}
              type="button"
              role="tab"
              aria-selected={priority === p}
              onClick={() => setPriority(p)}
              className={cn(
                'relative rounded-full px-4 py-2 text-sm font-medium capitalize transition-colors duration-200',
                priority === p ? 'text-[var(--text-primary)]' : 'text-[var(--text-muted)] hover:opacity-80',
              )}
            >
              {priority === p && (
                <motion.span
                  layoutId="priority-pill"
                  className="absolute inset-0 rounded-full bg-gradient-to-r from-[#3B82F6]/35 to-[#8B5CF6]/35 shadow-[0_0_24px_rgba(59,130,246,0.2)]"
                  transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                />
              )}
              <span className="relative z-10">{t(p as 'quality' | 'speed' | 'cost')}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <SectionLabel hint={t('useCaseHint')}>{t('useCase')}</SectionLabel>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {USE_CASE_IDS.map(({ id, titleKey, blurbKey, Icon }) => {
            const on = useCases.has(id);
            return (
              <button
                key={id}
                type="button"
                onClick={() => toggleUseCase(id)}
                className={cn(
                  'flex gap-3 rounded-xl border p-4 text-left transition-all duration-200',
                  on
                    ? 'border-[#3B82F6]/40 bg-gradient-to-br from-[#3B82F6]/10 to-[#8B5CF6]/10 shadow-[0_0_0_1px_rgba(59,130,246,0.15)]'
                    : 'border-[var(--border-subtle)] bg-[var(--surface-glass)] hover:border-[var(--surface-glass-hover)] hover:bg-[var(--surface-glass-hover)]',
                )}
              >
                <span
                  className={cn(
                    'flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border transition-colors',
                    on ? 'border-[#8B5CF6]/35 bg-[#8B5CF6]/15 text-[var(--text-accent-secondary)]' : 'border-[var(--border-subtle)] bg-[var(--surface-glass)] text-[var(--text-muted)]',
                  )}
                >
                  <Icon className="h-5 w-5" />
                </span>
                <span>
                  <span className="block text-sm font-semibold text-[var(--text-primary)]">{t(titleKey as TranslationKey)}</span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-[var(--text-muted)]">{t(blurbKey as TranslationKey)}</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="mb-6">
        <SectionLabel hint={t('providersHint')}>{t('preferredProviders')}</SectionLabel>
        <div className="flex flex-wrap gap-2">
          {PROVIDERS.map((name) => {
            const on = providers.has(name);
            return (
              <button
                key={name}
                type="button"
                onClick={() => toggleProvider(name)}
                className={cn(
                  'rounded-full border px-4 py-2 text-sm font-medium transition-all duration-200',
                  on
                    ? 'border-[#8B5CF6]/45 bg-[#8B5CF6]/15 text-[var(--text-primary)] shadow-[0_0_20px_rgba(139,92,246,0.15)]'
                    : 'border-[var(--border-subtle)] bg-[var(--surface-glass)] text-[var(--text-muted)] hover:border-[var(--surface-glass-hover)] hover:text-[var(--text-primary)]',
                )}
              >
                {name}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <SectionLabel hint={t('contextHint')}>{t('contextSize')}</SectionLabel>
        <div className="flex gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--segment-bg)] p-3 sm:p-4">
          {(['small', 'medium', 'large'] as const).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setContextSize(key)}
              className={cn(
                'flex-1 rounded-lg py-2.5 text-center text-sm font-medium capitalize transition-all duration-200',
                contextSize === key
                  ? 'bg-gradient-to-r from-[#3B82F6]/30 to-[#8B5CF6]/25 text-[var(--text-primary)] shadow-inner'
                  : 'text-[var(--text-muted)] hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)]',
              )}
            >
              {key}
            </button>
          ))}
        </div>
        <motion.p
          key={contextSize}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="mt-3 text-sm text-[var(--text-accent)]"
        >
          {t(CONTEXT_KEYS[contextSize] as TranslationKey)}
        </motion.p>
      </div>
    </motion.div>
  );
}
