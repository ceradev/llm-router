import { motion } from 'framer-motion';
import { useEffect, useId, useRef, useState } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import type { TranslationKey } from '../../i18n/translations';
import { cn } from '../../lib/cn';
import { IconChevronDown, IconInfo } from '../shared/icons';

export type Priority = 'quality' | 'speed' | 'cost';
export type UseCaseId = 'ide' | 'api' | 'chatbot' | 'batch';
export type ContextSize = 'small' | 'medium' | 'large';

const USE_CASE_IDS: { id: UseCaseId; titleKey: TranslationKey }[] = [
  { id: 'ide', titleKey: 'useCaseIde' },
  { id: 'api', titleKey: 'useCaseApi' },
  { id: 'chatbot', titleKey: 'useCaseChatbot' },
  { id: 'batch', titleKey: 'useCaseBatch' },
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
    <div className="mb-2.5 flex items-center gap-1.5">
      <span className="text-xs font-medium tracking-wide text-[var(--text-muted)]">{children}</span>
      <span className="group relative inline-flex">
        <button
          type="button"
          className="rounded p-0.5 text-[var(--text-muted)] opacity-60 transition-colors hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)]"
          aria-label={hint}
        >
          <IconInfo className="h-3.5 w-3.5" />
        </button>
        <span className="pointer-events-none absolute left-1/2 top-full z-10 mt-1 w-56 -translate-x-1/2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)]/95 px-2.5 py-2 text-xs leading-snug text-[var(--text-primary)] opacity-0 shadow-lg backdrop-blur-md transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
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
  const contextOrder: ContextSize[] = ['small', 'medium', 'large'];
  const contextProgress = contextOrder.indexOf(contextSize) / (contextOrder.length - 1);
  const [providersOpen, setProvidersOpen] = useState(false);
  const providersRef = useRef<HTMLDivElement>(null);
  const providersListId = useId();
  const selectedProviders = PROVIDERS.filter((name) => providers.has(name));

  useEffect(() => {
    if (!providersOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (providersRef.current && !providersRef.current.contains(e.target as Node)) {
        setProvidersOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setProvidersOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [providersOpen]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
      className="relative mt-6 overflow-visible rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-glass)] p-5 shadow-[var(--shadow-elevated)] backdrop-blur-xl sm:p-6"
    >
      <span
        aria-hidden
        className="pointer-events-none absolute -top-2.5 left-[28%] h-5 w-5 -translate-x-1/2 rotate-45 border-l border-t border-[var(--border-subtle)] bg-[var(--surface-glass)] sm:left-[32%]"
      />
      <div className="pointer-events-none absolute inset-y-0 left-[42%] w-40 bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.42),rgba(59,130,246,0.08)_45%,transparent_72%)] blur-2xl" />
      <div className="relative z-10 space-y-6">
      <div>
        <SectionLabel hint={t('priorityHint')}>{t('priority')}</SectionLabel>
        <div
          className="grid grid-cols-3 rounded-full border border-[var(--border-subtle)] bg-black/45 p-1"
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
                  className="absolute inset-0 rounded-full bg-white/18 shadow-[0_0_20px_rgba(59,130,246,0.25)]"
                  transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                />
              )}
              <span className="relative z-10">{t(p as 'quality' | 'speed' | 'cost')}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <SectionLabel hint={t('useCaseHint')}>{t('useCase')}</SectionLabel>
        <div className="grid grid-cols-4 gap-1.5 rounded-xl border border-[var(--border-subtle)] bg-black/45 p-1.5">
          {USE_CASE_IDS.map(({ id, titleKey }) => {
            const on = useCases.has(id);
            return (
              <button
                key={id}
                type="button"
                onClick={() => toggleUseCase(id)}
                className={cn(
                  'rounded-lg px-3 py-2.5 text-center text-sm font-medium transition-all duration-200 sm:px-4',
                  on
                    ? 'bg-white/16 text-[var(--text-primary)] shadow-[0_0_14px_rgba(59,130,246,0.18)]'
                    : 'text-[var(--text-muted)] hover:bg-white/10 hover:text-[var(--text-primary)]',
                )}
              >
                {t(titleKey)}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <SectionLabel hint={t('providersHint')}>{t('preferredProviders')}</SectionLabel>
        <div ref={providersRef} className="relative mt-0.5">
          <button
            type="button"
            className="flex w-full items-center justify-between gap-2 rounded-xl border border-[var(--border-subtle)] bg-black/45 p-2 text-left"
            onClick={() => setProvidersOpen((v) => !v)}
            aria-expanded={providersOpen}
            aria-controls={providersListId}
            aria-label={t('preferredProviders')}
          >
            <div className="flex min-h-11 flex-1 flex-wrap items-center gap-2.5">
              {selectedProviders.length > 0 ? (
                selectedProviders.map((name) => (
                  <span
                    key={name}
                    className="rounded-lg border border-[#3B82F6]/35 bg-[#1a2235] px-3.5 py-2 text-sm font-medium text-[var(--text-primary)]"
                  >
                    {name}
                  </span>
                ))
              ) : (
                <span className="px-2 text-sm text-[var(--text-muted)]/90">{t('preferredProviders')}</span>
              )}
            </div>
            <span className="rounded-md p-2 text-[var(--text-muted)] transition-colors hover:bg-white/15 hover:text-[var(--text-primary)]">
              <IconChevronDown className={cn('h-5 w-5 transition-transform', providersOpen ? 'rotate-180' : '')} />
            </span>
          </button>
          {providersOpen ? (
            <ul
              id={providersListId}
              className="absolute left-0 right-0 top-[calc(100%+0.45rem)] z-20 rounded-xl border border-[var(--border-subtle)] bg-[#070b16]/97 p-2 shadow-lg backdrop-blur-md"
            >
              {PROVIDERS.map((name) => {
                const on = providers.has(name);
                return (
                  <li key={name} className="mb-1 last:mb-0">
                    <button
                      type="button"
                      onClick={() => toggleProvider(name)}
                      className={cn(
                        'flex w-full items-center justify-between rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors',
                        on ? 'bg-[#1b2742] text-[var(--text-primary)]' : 'text-[var(--text-muted)] hover:bg-white/12 hover:text-[var(--text-primary)]',
                      )}
                    >
                      <span>{name}</span>
                      <span
                        className={cn(
                          'h-2.5 w-2.5 rounded-full transition-colors',
                          on ? 'bg-[#3B82F6]' : 'bg-transparent ring-1 ring-[var(--border-subtle)]',
                        )}
                      />
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
      </div>

      <div>
        <SectionLabel hint={t('contextHint')}>{t('contextSize')}</SectionLabel>
        <div className="rounded-xl border border-[var(--border-subtle)] bg-black/45 p-4">
          <div className="relative h-3 rounded-full bg-white/8">
            <motion.span
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[#1d4ed8] to-[#3b82f6]"
              animate={{ width: `${contextProgress * 100}%` }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
            />
            <div className="absolute inset-0 grid grid-cols-3">
              {contextOrder.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setContextSize(key)}
                  className="h-full w-full rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)]"
                  aria-label={`Set context size ${key}`}
                />
              ))}
            </div>
          </div>
          <div className="mt-2.5 grid grid-cols-3 text-xs font-medium text-[var(--text-muted)]">
            <span>Small</span>
            <span className="text-center">Medium</span>
            <span className="text-right">Large</span>
          </div>
        </div>
        <motion.p
          key={contextSize}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="mt-2.5 text-sm text-[var(--text-muted)]"
        >
          {t(CONTEXT_KEYS[contextSize] as TranslationKey)}
        </motion.p>
      </div>
      </div>
    </motion.div>
  );
}
