import { AnimatePresence, motion } from "framer-motion"
import { useState } from "react"

import { useI18n } from "@/contexts/I18nContext"
import { IconQuestionMark } from "@/shared/components"
import type { TranslationKey } from "@/i18n/translations"

type FaqItem = {
  titleKey: TranslationKey
  bodyKey: TranslationKey
}

const FAQ_ITEMS: FaqItem[] = [
  { titleKey: "faqWhatTitle", bodyKey: "faqWhatBody" },
  { titleKey: "faqHowTitle", bodyKey: "faqHowBody" },
  { titleKey: "faqFreeTitle", bodyKey: "faqFreeBody" },
  { titleKey: "faqModelsTitle", bodyKey: "faqModelsBody" },
]

export function FaqDrawer({
  open,
  onClose,
}: Readonly<{
  open: boolean
  onClose: () => void
}>) {
  const { t } = useI18n()
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)

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
            aria-label="Close FAQ"
          />
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="faq-title"
            className="fixed right-0 top-0 z-50 flex h-dvh w-[min(100%,380px)] flex-col border-l border-(--border-subtle) bg-(--surface-glass) shadow-(--shadow-drawer) backdrop-blur-xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 320 }}
          >
            <div className="flex items-center justify-between border-b border-(--border-subtle) px-5 py-4">
              <div className="flex items-center gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-(--surface-glass-hover) text-(--text-accent)">
                  <IconQuestionMark className="h-5 w-5" />
                </span>
                <h2
                  id="faq-title"
                  className="text-lg font-semibold tracking-tight text-(--text-primary)"
                >
                  {t("faqTitle")}
                </h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="min-h-11 rounded-lg px-3 py-2 text-sm text-(--text-muted) transition-colors hover:bg-(--surface-glass-hover) hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
              >
                {t("close")}
              </button>
            </div>
            <ul className="flex-1 overflow-y-auto p-3">
              {FAQ_ITEMS.map((item, index) => {
                const isExpanded = expandedIndex === index
                return (
                  <motion.li
                    key={item.titleKey}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.03 * index, duration: 0.2 }}
                    className="mb-2"
                  >
                    <button
                      type="button"
                      onClick={() => setExpandedIndex(isExpanded ? null : index)}
                      className="flex w-full items-center justify-between rounded-xl border border-(--border-subtle) bg-(--surface-glass) p-4 text-left transition-colors hover:bg-(--surface-glass-hover)"
                      aria-expanded={isExpanded}
                    >
                      <span className="text-sm font-medium text-(--text-primary)">
                        {t(item.titleKey)}
                      </span>
                      <span
                        className={`shrink-0 text-(--text-muted) transition-transform duration-200 ${
                          isExpanded ? "rotate-180" : ""
                        }`}
                      >
                        <svg
                          className="h-4 w-4"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth={2}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="m19 9-7 7-7-7"
                          />
                        </svg>
                      </span>
                    </button>
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <p className="px-4 pb-4 pt-2 text-sm leading-relaxed text-(--text-muted)">
                            {t(item.bodyKey)}
                          </p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.li>
                )
              })}
            </ul>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}

export function FloatingButtons({
  onFaqClick,
  onScrollToTop,
  isAtTop,
  hideFaq,
}: Readonly<{
  onFaqClick: () => void
  onScrollToTop: () => void
  isAtTop: boolean
  hideFaq?: boolean
}>) {
  const { t } = useI18n()

  return (
    <div className="fixed bottom-6 right-6 z-30 flex flex-col gap-3">
      <AnimatePresence initial={false}>
        {!isAtTop && (
          <motion.button
            key="scroll-to-top"
            type="button"
            onClick={onScrollToTop}
            initial={{ opacity: 0, y: 12, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.92 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="flex h-12 w-12 shrink-0 cursor-pointer items-center justify-center rounded-full border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) shadow-lg backdrop-blur-md transition-colors hover:bg-(--surface-glass-hover) hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
            aria-label={t("startOver")}
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m4.5 18.75 7.5-7.5 7.5 7.5"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m4.5 12.75 7.5-7.5 7.5 7.5"
              />
            </svg>
          </motion.button>
        )}
      </AnimatePresence>
      {hideFaq ? null : (
        <button
          type="button"
          onClick={onFaqClick}
          className="flex h-12 w-12 shrink-0 cursor-pointer items-center justify-center rounded-full border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) shadow-lg backdrop-blur-md transition-colors hover:bg-(--surface-glass-hover) hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
          aria-label={t("faq")}
        >
          <IconQuestionMark className="h-5 w-5" />
        </button>
      )}
    </div>
  )
}