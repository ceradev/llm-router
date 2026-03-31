import type { AdminTab } from "./types"

export const tabs: Array<{ key: AdminTab; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "models", label: "Models" },
  { key: "requests", label: "Requests" },
  { key: "sync", label: "Sync" },
]

export const fieldClass =
  "rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-3 py-2 text-sm text-(--text-primary) placeholder:text-(--text-muted) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"

export const actionButtonClass =
  "rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-4 py-2 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--surface-glass-hover) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
