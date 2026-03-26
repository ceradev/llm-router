import { motion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import type { ModelDecision } from "@/features/results/types"

function ActionButton({
  label,
  href,
}: Readonly<{ label: string; href?: string }>) {
  const className =
    "rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-4 py-2.5 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--surface-glass-hover) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"

  if (href) {
    return (
      <a
        className={className}
        href={href}
        target="_blank"
        rel="noreferrer"
      >
        {label}
      </a>
    )
  }

  return (
    <button type="button" className={className}>
      {label}
    </button>
  )
}

export function FreeAlternativeCard({
  model,
}: Readonly<{
  model: ModelDecision
}>) {
  const { t } = useI18n()

  const runLocal = model.actions?.find((a) => a.kind === "runLocal")
  const useFreeApi = model.actions?.find((a) => a.kind === "useFreeApi")

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-5 shadow-(--shadow-elevated) backdrop-blur-xl sm:p-6"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            {t("freeAlternative")}
          </p>
          <h3 className="mt-2 text-lg font-semibold text-(--text-primary) sm:text-xl">
            {model.name}
          </h3>
          <p className="mt-1 text-sm text-(--text-muted)">{model.provider}</p>
        </div>

        {(runLocal || useFreeApi) && (
          <div className="flex flex-wrap gap-2">
            {runLocal && (
              <ActionButton label={runLocal.label} href={runLocal.href} />
            )}
            {useFreeApi && (
              <ActionButton label={useFreeApi.label} href={useFreeApi.href} />
            )}
          </div>
        )}
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            {t("pros")}
          </p>
          <ul className="mt-2 space-y-1.5 text-sm text-(--text-primary)">
            <li className="flex gap-2">
              <span className="select-none text-emerald-400">✔</span>
              <span>{t("freeAltProNoCost")}</span>
            </li>
            <li className="flex gap-2">
              <span className="select-none text-emerald-400">✔</span>
              <span>{t("freeAltProLocalOrFreeApi")}</span>
            </li>
          </ul>
        </div>

        <div className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            {t("cons")}
          </p>
          <ul className="mt-2 space-y-1.5 text-sm text-(--text-primary)">
            <li className="flex gap-2">
              <span className="select-none text-rose-400">✖</span>
              <span>{t("freeAltConLowerAccuracy")}</span>
            </li>
            <li className="flex gap-2">
              <span className="select-none text-rose-400">✖</span>
              <span>{t("freeAltConSlower")}</span>
            </li>
          </ul>
        </div>
      </div>
    </motion.section>
  )
}

