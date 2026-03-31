export function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10)
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

export function statusBadgeClass(status: string): string {
  if (status === "success") return "text-emerald-300 border-emerald-400/30 bg-emerald-500/10"
  if (status === "fallback") return "text-amber-300 border-amber-400/30 bg-amber-500/10"
  if (status === "error") return "text-rose-300 border-rose-400/30 bg-rose-500/10"
  return "text-(--text-muted) border-(--border-subtle) bg-(--surface-glass)"
}

export function modelStatusBadgeClass(status: string): string {
  if (status === "verified") return "text-emerald-300 border-emerald-400/30 bg-emerald-500/10"
  if (status === "provisional") return "text-amber-300 border-amber-400/30 bg-amber-500/10"
  if (status === "cataloged") return "text-sky-300 border-sky-400/30 bg-sky-500/10"
  if (status === "rejected") return "text-rose-300 border-rose-400/30 bg-rose-500/10"
  return "text-(--text-muted) border-(--border-subtle) bg-(--surface-glass)"
}
