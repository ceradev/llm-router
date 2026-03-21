import { useI18n } from '../../../contexts/I18nContext';
import { HistoryTrigger } from '../../panels/HistoryDrawer';
import { NavbarToolbar } from '../../shell/NavbarControls';

type Props = {
  onHistoryOpen: () => void;
  historyOpen: boolean;
};

export function HeroNavbar({ onHistoryOpen, historyOpen }: Props) {
  const { t } = useI18n();

  return (
    <header className="mb-10 flex justify-center sm:mb-12">
      <nav
        className="flex w-full max-w-xl items-center justify-between gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-glass)] px-3 py-2 pl-5 shadow-[var(--shadow-navbar)] backdrop-blur-xl sm:max-w-2xl sm:px-4 sm:py-2.5"
        aria-label="Primary"
      >
        <span className="text-lg font-semibold tracking-tight text-[var(--text-primary)] sm:text-xl">{t('appName')}</span>
        <NavbarToolbar
          historySlot={<HistoryTrigger onClick={onHistoryOpen} expanded={historyOpen} />}
        />
      </nav>
    </header>
  );
}
