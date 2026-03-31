import type { AdminMetricsSummary } from "@/shared/api/admin"

import type { OverviewCard } from "@/features/admin/types"

export function OverviewTab({
  overviewCards,
  metrics,
}: Readonly<{
  overviewCards: OverviewCard[]
  metrics: AdminMetricsSummary | null
}>) {
  return (
    <section className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {overviewCards.map((card) => (
          <article
            key={card.label}
            className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-md"
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
              {card.label}
            </p>
            <p className="mt-2 text-3xl font-semibold text-(--text-primary)">{card.value}</p>
          </article>
        ))}
      </div>
      <article className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-md">
        <h2 className="mb-3 text-base font-semibold text-(--text-primary)">7-Day Quick Metrics</h2>
        <pre className="overflow-auto rounded-xl border border-(--border-subtle) bg-black/20 p-3 text-xs text-(--text-muted)">
          {JSON.stringify(metrics, null, 2)}
        </pre>
      </article>
    </section>
  )
}
