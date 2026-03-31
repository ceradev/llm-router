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
          className={`flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-lg border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) transition-colors hover:bg-(--surface-glass-hover) hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus) ${
            expanded ? "bg-[#3B82F6]/15 text-(--text-accent)" : ""
          }`}
          aria-label={t("openHistory")}
          aria-haspopup="dialog"
          aria-expanded={expanded}
        >
          <IconClock className="h-5 w-5" />
        </button>
        <span className="pointer-events-none absolute left-1/2 top-[calc(100%+0.45rem)] z-60 -translate-x-1/2 rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2 py-1 text-[11px] font-medium whitespace-nowrap text-(--text-primary) opacity-0 shadow-lg backdrop-blur-md transition-all duration-150 group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100">
          {historyTooltip}
        </span>
      </div>
    )
  }