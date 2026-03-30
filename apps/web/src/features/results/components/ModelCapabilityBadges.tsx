import { useI18n } from "@/contexts/I18nContext"
import type { ModelDecision } from "@/features/results/types"
import {
  labelCapability,
  labelModelTypeLabel,
  labelPublicStatus,
} from "@/features/results/utils/routingLabels"

function TierBadge({ tier, isFree }: Readonly<{ tier?: string; isFree?: boolean }>) {
  const { t } = useI18n()
  if (isFree || tier === "free") {
    return (
      <span className="rounded-md bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
        {t("tierFree")}
      </span>
    )
  }
  if (tier === "premium") {
    return (
      <span className="rounded-md bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400">
        {t("tierPremium")}
      </span>
    )
  }
  if (tier === "alternative") {
    return (
      <span className="rounded-md bg-(--badge-bg) px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-(--text-muted)">
        {t("tierAlternative")}
      </span>
    )
  }
  return null
}

function PublicStatusBadge({ statusKey }: Readonly<{ statusKey: string }>) {
  const { t } = useI18n()
  const base =
    "rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
  if (statusKey === "verified") {
    return (
      <span className={`${base} bg-emerald-500/12 text-emerald-700 dark:text-emerald-300`}>
        {labelPublicStatus(statusKey, t)}
      </span>
    )
  }
  if (statusKey === "provisional") {
    return (
      <span className={`${base} bg-amber-500/15 text-amber-800 dark:text-amber-300`}>
        {labelPublicStatus(statusKey, t)}
      </span>
    )
  }
  if (statusKey === "available") {
    return (
      <span className={`${base} border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted)`}>
        {labelPublicStatus(statusKey, t)}
      </span>
    )
  }
  if (statusKey === "deprecated") {
    return (
      <span className={`${base} bg-rose-500/10 text-rose-700 dark:text-rose-300`}>
        {labelPublicStatus(statusKey, t)}
      </span>
    )
  }
  return (
    <span className={`${base} border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted)`}>
      {labelPublicStatus(statusKey, t)}
    </span>
  )
}

export function ModelCapabilityBadges({
  model,
  className = "",
}: Readonly<{
  model: ModelDecision
  className?: string
}>) {
  const { t } = useI18n()
  const caps = model.modelCategories?.length ? model.modelCategories : (model.capabilities ?? [])
  const typeLabels = model.modelTypeLabels ?? []
  const useServerTypeLabels = typeLabels.length > 0

  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className}`}>
      <TierBadge tier={model.tier} isFree={model.isFreeTier} />
      {model.publicStatusKey ? <PublicStatusBadge statusKey={model.publicStatusKey} /> : null}
      {useServerTypeLabels ? (
        typeLabels.map((key) => (
          <span
            key={key}
            className="rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2 py-0.5 text-[10px] font-medium text-(--text-muted)"
          >
            {labelModelTypeLabel(key, t)}
          </span>
        ))
      ) : (
        <>
          {model.supportsJson ? (
            <span className="rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2 py-0.5 text-[10px] font-medium text-(--text-muted)">
              {t("badgeJson")}
            </span>
          ) : null}
          {model.supportsTools ? (
            <span className="rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2 py-0.5 text-[10px] font-medium text-(--text-muted)">
              {t("badgeTools")}
            </span>
          ) : null}
          {caps
            .filter((c) => c !== "general")
            .slice(0, 4)
            .map((c) => (
              <span
                key={c}
                className="rounded-md border border-(--border-subtle) bg-(--surface-glass) px-2 py-0.5 text-[10px] font-medium text-(--text-muted)"
              >
                {labelCapability(c, t)}
              </span>
            ))}
        </>
      )}
    </div>
  )
}
