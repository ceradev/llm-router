import type { AdminSyncResult } from "@/shared/api/admin"

import { actionButtonClass } from "@/features/admin/constants"

export function SyncTab({
  syncRunning,
  syncResult,
  onRunSync,
}: Readonly<{
  syncRunning: boolean
  syncResult: AdminSyncResult | null
  onRunSync: () => void
}>) {
  return (
    <section className="space-y-4 rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-md">
      <p className="text-sm text-(--text-muted)">
        Ejecuta una sincronización manual del catálogo con OpenRouter.
      </p>
      <button
        type="button"
        className={`${actionButtonClass} disabled:cursor-not-allowed disabled:opacity-50`}
        onClick={onRunSync}
        disabled={syncRunning}
      >
        {syncRunning ? "Running..." : "Run OpenRouter Sync"}
      </button>
      {syncResult ? (
        <article className="rounded-xl border border-(--border-subtle) bg-black/20 p-3">
          <pre className="overflow-auto text-xs text-(--text-muted)">{JSON.stringify(syncResult, null, 2)}</pre>
        </article>
      ) : null}
    </section>
  )
}
