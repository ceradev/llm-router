import { useI18n } from '../../../contexts/I18nContext';

type Props = {
  prompt: string;
  setPrompt: (v: string) => void;
};

export function HeroPromptField({ prompt, setPrompt }: Readonly<Props>) {
  const { t } = useI18n();

  return (
    <div className="px-3 sm:px-4">
      <label htmlFor="prompt" className="sr-only">
        {t('promptLabel')}
      </label>
      <textarea
        id="prompt"
        rows={9}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder={t('promptPlaceholder')}
        className="w-full resize-none rounded-2xl border border-(--border-subtle) bg-(--surface-glass) px-4 py-4 text-base leading-relaxed text-(--text-primary) shadow-(--shadow-prompt) outline-none backdrop-blur-lg transition-[box-shadow,border-color] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] placeholder:text-(--text-muted) focus:border-(#3B82F6)/45 focus:shadow-(--shadow-prompt-focus) sm:px-5 sm:py-5"
      />
    </div>
  );
}
