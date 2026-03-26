import { AnimatePresence, motion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import { IconClock } from "@/shared/components"
import { HISTORY_MOCK } from "../data/mock"
import type { HistoryItem } from "../types"

type Props = {
  open: boolean
  onClose: () => void
  onRerun?: (item: HistoryItem) => void
  onView?: (item: HistoryItem) => void
}

export function HistoryDrawer({ open, onClose, onRerun, onView }: Readonly<Props>) {
  const { t } = useI18n()

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            className="fixed inset-0 z-40 bg-(--scrim) backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            aria-label="Close history"
          />
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="history-title"
            className="fixed right-0 top-0 z-50 flex h-dvh w-[min(100%,380px)] flex-col border-l border-(--border-subtle) bg-(--surface-glass) shadow-(--shadow-drawer) backdrop-blur-xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 320 }}
          >
            <div className="flex items-center justify-between border-b border-(--border-subtle) px-5 py-4">
              <div className="flex items-center gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-(--surface-glass-hover) text-(--text-accent)">
                  <IconClock className="h-5 w-5" />
                </span>
                <h2
                  id="history-title"
                  className="text-lg font-semibold tracking-tight text-(--text-primary)"
                >
                  {t("history")}
                </h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg px-3 py-2 text-sm text-(--text-muted) transition-colors hover:bg-(--surface-glass-hover) hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
              >
                {t("close")}
              </button>
            </div>
            <ul className="flex-1 overflow-y-auto p-3">
              {HISTORY_MOCK.map((item: HistoryItem, i: number) => (
                <motion.li
                  key={item.id}
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 * i, duration: 0.25, ease: "easeOut" }}
                  className="mb-2"
                >
                  <div className="group rounded-xl border border-(--border-subtle) bg-(--surface-glass) p-4 transition-colors hover:border-(--surface-glass-hover) hover:bg-(--surface-glass-hover)">
                    <p className="line-clamp-2 text-sm leading-relaxed text-(--text-primary)">
                      {item.prompt}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-(--text-muted)">
                      <span className="rounded-md bg-[#3B82F6]/15 px-2 py-0.5 font-medium text-(--text-accent)">
                        {item.model}
                      </span>
                      <span>{item.timeAgo}</span>
                    </div>
                    <div className="mt-3 flex gap-2 opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100">
                      <button
                        type="button"
                        className="rounded-lg bg-(--surface-glass-hover) px-3 py-1.5 text-xs font-medium text-(--text-primary) transition-colors hover:bg-[#3B82F6]/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0EA5E9]/70"
                        onClick={() => onRerun?.(item)}
                      >
                        {t("rerun")}
                      </button>
                      <button
                        type="button"
                        className="rounded-lg bg-(--surface-glass-hover) px-3 py-1.5 text-xs font-medium text-(--text-primary) transition-colors hover:bg-[#0EA5E9]/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0EA5E9]/70"
                        onClick={() => onView?.(item)}
                      >
                        {t("view")}
                      </button>
                    </div>
                  </div>
                </motion.li>
              ))}
            </ul>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}

