import { motion } from 'framer-motion';
import { useI18n } from '../../../contexts/I18nContext';
import { heroHeadlineTransition } from './heroMotion';

export function HeroHeadline() {
  const { t } = useI18n();

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={heroHeadlineTransition}
      className="text-center"
    >
      <h1 className="text-balance bg-linear-to-r from-(--headline-from) via-(--headline-via) to-(--headline-to) bg-clip-text text-3xl font-semibold tracking-[-0.04em] text-transparent sm:text-4xl md:text-6xl sm:leading-tight">
        <span className="block">{t('heroLine1')}</span>
        <span className="block">{t('heroLine2')}</span>
      </h1>
      <p className="mx-auto mt-3 max-w-2xl text-pretty text-base bg-linear-to-r from-(--headline-from) via-(--headline-via) to-(--headline-to) bg-clip-text text-transparent sm:text-lg md:text-3xl leading-relaxed tracking-[-0.02em]">
        {t('heroSubtitle')}
      </p>
    </motion.div>
  );
}
