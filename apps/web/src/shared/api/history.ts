import { getSessionId } from "./session"
import type { HistoryItem } from "@/features/history/types"

const API_BASE = import.meta.env.PUBLIC_API_BASE_URL as string

type BackendRequest = {
  id: string
  prompt: string
  selected_model: string | null
  created_at: string
}

type BackendHistoryResponse = {
  items: BackendRequest[]
  total: number
  limit: number
  offset: number
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "Just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days === 1) return "Yesterday"
  return `${days}d ago`
}

function formatModelName(modelId: string | null): string {
  if (!modelId) return "N/A"
  const name = modelId.split("/").pop() ?? modelId
  return name.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

export async function fetchHistory(limit = 20, offset = 0): Promise<HistoryItem[]> {
  const res = await fetch(`${API_BASE}/v1/requests?limit=${limit}&offset=${offset}`, {
    headers: { "X-Session-Id": getSessionId() },
  })
  if (!res.ok) return []
  const data: BackendHistoryResponse = await res.json()
  return data.items.map((item) => ({
    id: item.id,
    prompt: item.prompt,
    model: formatModelName(item.selected_model),
    timeAgo: formatTimeAgo(item.created_at),
  }))
}
