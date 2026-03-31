import type { ResultsDecisionPayload } from "@/features/results/types"

const STORAGE_KEY = "llm-router-history-results-cache"
const MAX_ENTRIES = 30

type CacheEntry = {
  requestId: string
  payload: ResultsDecisionPayload
  savedAt: number
}

function readCache(): CacheEntry[] {
  if (globalThis.window === undefined) return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as CacheEntry[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeCache(entries: CacheEntry[]): void {
  if (globalThis.window === undefined) return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
  } catch {
    // ignore storage failures
  }
}

export function saveHistoryResult(payload: ResultsDecisionPayload): void {
  const requestId = payload.routing?.requestId
  if (!requestId) return

  const current = readCache().filter((entry) => entry.requestId !== requestId)
  current.unshift({
    requestId,
    payload,
    savedAt: Date.now(),
  })
  writeCache(current.slice(0, MAX_ENTRIES))
}

export function getHistoryResult(requestId: string): ResultsDecisionPayload | null {
  const found = readCache().find((entry) => entry.requestId === requestId)
  return found?.payload ?? null
}

