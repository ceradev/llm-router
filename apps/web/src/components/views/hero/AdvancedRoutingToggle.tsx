import { motion } from 'framer-motion';
import { useI18n } from '../../../contexts/I18nContext';
import { advancedToggleThumbSpring } from './heroMotion';

type Props = {
  advancedOpen: boolean;
  setAdvancedOpen: (v: boolean) => void;
};

export function AdvancedRoutingToggle({ advancedOpen, setAdvancedOpen }: Props) {
  const { t } = useI18n();

  return (
    <button
      type="button"
      role="switch"
      aria-checked={advancedOpen}
      onClick={() => setAdvancedOpen(!advancedOpen)}
      className="group flex items-center gap-3 rounded-full border border-transparent px-1 py-1 text-left transition-colors hover:border-[var(--border-subtle)]"
    >
      <span
        className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors duration-200 ${
          advancedOpen ? 'bg-[#3B82F6]/35' : 'bg-[var(--surface-glass-hover)]'
        }`}
      >
        <motion.span
          layout
          className="inline-block h-5 w-5 rounded-full bg-[var(--text-primary)] shadow-md"
          animate={{ x: advancedOpen ? 24 : 4 }}
          transition={advancedToggleThumbSpring}
        />
      </span>
      <span className="text-sm font-medium text-[var(--text-muted)] transition-colors group-hover:text-[var(--text-primary)] sm:text-base">
        {t('advancedOptions')}
      </span>
    </button>
  );
}
