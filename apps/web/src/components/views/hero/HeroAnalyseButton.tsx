import { motion } from 'framer-motion';
import { useI18n } from '../../../contexts/I18nContext';
import {
  analyseButtonSpring,
  analyseHoverWhile,
  analyseShineTransition,
  analyseTapWhile,
} from './heroMotion';

type Props = {
  onClick: () => void;
  canSubmit: boolean;
};

export function HeroAnalyseButton({ onClick, canSubmit }: Props) {
  const { t } = useI18n();

  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={!canSubmit}
      whileHover={canSubmit ? analyseHoverWhile : undefined}
      whileTap={canSubmit ? analyseTapWhile : undefined}
      transition={analyseButtonSpring}
      className="relative overflow-hidden rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] px-8 py-3.5 text-sm font-semibold text-white shadow-[0_12px_40px_rgba(59,130,246,0.26)] transition-shadow duration-200 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none sm:px-10 sm:py-4 sm:text-base"
    >
      <span className="relative z-10">{t('analyse')}</span>
      <motion.span
        className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0"
        initial={{ x: '-100%' }}
        whileHover={canSubmit ? { x: '100%' } : undefined}
        transition={analyseShineTransition}
      />
    </motion.button>
  );
}
