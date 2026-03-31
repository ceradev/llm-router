import type { AdminRequestList } from "@/shared/api/admin"

import { actionButtonClass, fieldClass } from "@/features/admin/constants"
import { statusBadgeClass } from "@/features/admin/utils"

export function RequestsTab({
  requestsDate,
  requestsLimit,
  requests,
  onRequestsDate,
  onRequestsLimit,
  onLoadRequests,
}: Readonly<{
  requestsDate: string
  requestsLimit: number
  requests: AdminRequestList | null
  onRequestsDate: (value: string) => void
  onRequestsLimit: (value: number) => void
  onLoadRequests: () => void
}>) {
  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-md">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-(--text-muted)">Query</p>
        <div className="flex flex-wrap gap-2">
          <input
            type="date"
            value={requestsDate}
            onChange={(event) => onRequestsDate(event.target.value)}
            className={fieldClass}
          />
          <input
            type="number"
            value={requestsLimit}
            min={1}
            max={100}
            onChange={(event) => onRequestsLimit(Number(event.target.value))}
            className={`${fieldClass} w-32`}
          />
          <button type="button" className={actionButtonClass} onClick={onLoadRequests}>
            Load Requests
          </button>
        </div>
      </div>
      <article className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-md">
        <div className="mb-3 flex flex-wrap gap-2">
          {(requests?.items ?? []).slice(0, 6).map((item) => (
            <span
              key={item.id}
              className={`rounded-full border px-2 py-1 text-[11px] uppercase tracking-wide ${statusBadgeClass(item.status)}`}
            >
              {item.status}
            </span>
          ))}
        </div>
        <pre className="overflow-auto rounded-xl border border-(--border-subtle) bg-black/20 p-3 text-xs text-(--text-muted)">
          {JSON.stringify(requests, null, 2)}
        </pre>
      </article>
    </section>
  )
}
