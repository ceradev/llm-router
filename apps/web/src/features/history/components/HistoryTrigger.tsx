import { useI18n } from "@/contexts/I18nContext"
import { IconClock } from "@/shared/components"

export function HistoryTrigger({
    onClick,
    expanded,
  }: Readonly<{
    onClick: () => void
    expanded: boolean
  }>) {
    const { t } = useI18n()
    const historyTooltip = expanded ? t("closeHistory") : t("openHistory")
  
    return (
      <div className="group relative inline-flex">
        <button
          type="button"
          onClick={onClick}
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-glass)] text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring-focus)] ${
            expanded ? "bg-[#3B82F6]/15 text-[var(--text-accent)]" : ""
          }`}
          aria-label={t("openHistory")}
          aria-haspopup="dialog"
          aria-expanded={expanded}
        >
          <IconClock className="h-5 w-5" />
        </button>
        <span className="pointer-events-none absolute left-1/2 top-[calc(100%+0.45rem)] z-60 -translate-x-1/2 rounded-md border border-[var(--border-subtle)] bg-[var(--surface-glass)] px-2 py-1 text-[11px] font-medium whitespace-nowrap text-[var(--text-primary)] opacity-0 shadow-lg backdrop-blur-md transition-all duration-150 group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100">
          {historyTooltip}
        </span>
      </div>
    )
  }