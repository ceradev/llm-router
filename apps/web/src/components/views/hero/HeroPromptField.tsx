import { useI18n } from '../../../contexts/I18nContext';

type Props = {
  prompt: string;
  setPrompt: (v: string) => void;
};

export function HeroPromptField({ prompt, setPrompt }: Props) {
  const { t } = useI18n();

  return (
    <>
      <label htmlFor="prompt" className="sr-only">
        {t('promptLabel')}
      </label>
      <textarea
        id="prompt"
        rows={9}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder={t('promptPlaceholder')}
        className="w-full resize-y rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-glass)] px-4 py-4 text-base leading-relaxed text-[var(--text-primary)] shadow-[var(--shadow-prompt)] outline-none backdrop-blur-xl transition-[box-shadow,border-color] duration-300 placeholder:text-[var(--text-muted)] focus:border-[#3B82F6]/55 focus:shadow-[var(--shadow-prompt-focus)] sm:px-5 sm:py-5"
      />
    </>
  );
}
