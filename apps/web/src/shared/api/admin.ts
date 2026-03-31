const API_BASE = import.meta.env.PUBLIC_API_BASE_URL as string
const ADMIN_API_KEY = (import.meta.env.PUBLIC_ADMIN_API_KEY as string | undefined) ?? ""

type AdminRequestStatus = "success" | "fallback" | "error" | "pending"

export type AdminDashboard = {
  total_models: number
  total_providers: number
  requests_today: number
  success_rate: number
}

export type AdminModelListItem = {
  routing_key: string
  display_name: string
  provider: string
  tier: string
  is_available: boolean
  supports_json: boolean
  supports_tools: boolean
  supports_vision: boolean
  input_modalities: string[]
  output_modalities: string[]
  evaluation_status: string
}

export type AdminModelDetail = {
  routing_key: string
  display_name: string
  provider: string
  tier: string
  is_available: boolean
  supports_vision: boolean
  input_modalities: string[]
  output_modalities: string[]
  evaluation_status: string
  selected_count: number
  average_rating: number | null
  rating_count: number
}

export type AdminRequestListItem = {
  id: string
  prompt: string
  selected_model: string | null
  status: AdminRequestStatus
  created_at: string
}

export type AdminRequestList = {
  date: string
  limit: number
  items: AdminRequestListItem[]
}

export type AdminSyncResult = {
  models_processed: number
  models_created: number
  models_updated: number
}

export type AdminEvaluationMode = "heuristic" | "live"

export type AdminModelEvaluationResult = {
  routing_key: string
  mode: AdminEvaluationMode
  benchmark_run_id: number
  benchmark_status: string
  benchmark_scope: string
  passed: boolean
  evaluation_status_after: string
  skip_reason?: string | null
  cases: Array<{
    id: string
    ok: boolean
    detail: string
    latency_ms: number
    input_tokens: number
    output_tokens: number
    cost_usd: number
  }>
}

export type AdminBatchEvaluationResult = {
  mode: AdminEvaluationMode
  matched_models: number
  processed_models: number
  succeeded: number
  failed: number
  skipped: number
  benchmark_status_counts: Record<string, number>
  skip_reason_counts?: Record<string, number>
  skipped_models?: Array<{ routing_key: string; reason: string }>
  failed_reason_counts?: Record<string, number>
  failed_models?: Array<{ routing_key: string; reason: string }>
  error_messages: string[]
}

export type AdminMetricsSummary = {
  days: number
  total_requests: number
  successful_requests: number
  failed_requests: number
  success_rate: number
  avg_latency_ms: number
  unique_sessions_peak: number
}

function adminHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-Admin-Key": ADMIN_API_KEY,
  }
}

async function parseJson<T>(res: Response, context: string): Promise<T> {
  if (!res.ok) throw new Error(`${context} ${res.status}`)
  return res.json() as Promise<T>
}

export async function fetchAdminDashboard(signal?: AbortSignal): Promise<AdminDashboard> {
  const res = await fetch(`${API_BASE}/v1/admin/dashboard`, {
    headers: adminHeaders(),
    signal,
  })
  return parseJson<AdminDashboard>(res, "Admin dashboard")
}

export async function fetchAdminModels(params?: {
  provider?: string
  tier?: string
  available?: boolean
  evaluation_status?: string
}): Promise<AdminModelListItem[]> {
  const query = new URLSearchParams()
  if (params?.provider) query.set("provider", params.provider)
  if (params?.tier) query.set("tier", params.tier)
  if (params?.available !== undefined) query.set("available", String(params.available))
  if (params?.evaluation_status) query.set("evaluation_status", params.evaluation_status)
  const suffix = query.toString() ? `?${query.toString()}` : ""
  const res = await fetch(`${API_BASE}/v1/admin/models${suffix}`, {
    headers: adminHeaders(),
  })
  return parseJson<AdminModelListItem[]>(res, "Admin models")
}

export async function runAdminModelEvaluation(
  routingKey: string,
  mode: AdminEvaluationMode,
  options?: {
    enableImageTextV2?: boolean
    strictImageTextChecks?: boolean
    enableFileTextV3?: boolean
    strictFileTextChecks?: boolean
  },
): Promise<AdminModelEvaluationResult> {
  const encoded = routingKey
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/")
  const query = new URLSearchParams({ mode })
  if (options?.enableImageTextV2 !== undefined) {
    query.set("enable_image_text_v2", String(options.enableImageTextV2))
  }
  if (options?.strictImageTextChecks !== undefined) {
    query.set("strict_image_text_checks", String(options.strictImageTextChecks))
  }
  if (options?.enableFileTextV3 !== undefined) {
    query.set("enable_file_text_v3", String(options.enableFileTextV3))
  }
  if (options?.strictFileTextChecks !== undefined) {
    query.set("strict_file_text_checks", String(options.strictFileTextChecks))
  }
  const res = await fetch(`${API_BASE}/v1/admin/models/${encoded}/evaluate?${query.toString()}`, {
    method: "POST",
    headers: adminHeaders(),
  })
  return parseJson<AdminModelEvaluationResult>(res, "Admin model evaluation")
}

export async function runAdminBatchEvaluation(options: {
  mode: AdminEvaluationMode
  provider?: string
  evaluationStatus?: string
  limit?: number
  enableImageTextV2?: boolean
  strictImageTextChecks?: boolean
  enableFileTextV3?: boolean
  strictFileTextChecks?: boolean
}): Promise<AdminBatchEvaluationResult> {
  const query = new URLSearchParams({ mode: options.mode })
  if (options.provider) query.set("provider", options.provider)
  if (options.evaluationStatus) query.set("evaluation_status", options.evaluationStatus)
  if (options.limit !== undefined) query.set("limit", String(options.limit))
  if (options.enableImageTextV2 !== undefined) {
    query.set("enable_image_text_v2", String(options.enableImageTextV2))
  }
  if (options.strictImageTextChecks !== undefined) {
    query.set("strict_image_text_checks", String(options.strictImageTextChecks))
  }
  if (options.enableFileTextV3 !== undefined) {
    query.set("enable_file_text_v3", String(options.enableFileTextV3))
  }
  if (options.strictFileTextChecks !== undefined) {
    query.set("strict_file_text_checks", String(options.strictFileTextChecks))
  }
  const res = await fetch(`${API_BASE}/v1/admin/models/evaluate-batch?${query.toString()}`, {
    method: "POST",
    headers: adminHeaders(),
  })
  return parseJson<AdminBatchEvaluationResult>(res, "Admin batch evaluation")
}

export async function fetchAdminModelDetail(routingKey: string): Promise<AdminModelDetail> {
  const encoded = routingKey
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/")
  const res = await fetch(`${API_BASE}/v1/admin/models/${encoded}`, {
    headers: adminHeaders(),
  })
  return parseJson<AdminModelDetail>(res, "Admin model detail")
}

export async function fetchAdminRequests(date: string, limit = 20): Promise<AdminRequestList> {
  const query = new URLSearchParams({ date, limit: String(limit) })
  const res = await fetch(`${API_BASE}/v1/admin/requests?${query.toString()}`, {
    headers: adminHeaders(),
  })
  return parseJson<AdminRequestList>(res, "Admin requests")
}

export async function runAdminSync(): Promise<AdminSyncResult> {
  const res = await fetch(`${API_BASE}/v1/admin/sync/run`, {
    method: "POST",
    headers: adminHeaders(),
  })
  return parseJson<AdminSyncResult>(res, "Admin sync")
}

export async function fetchAdminMetrics(days = 7): Promise<AdminMetricsSummary> {
  const res = await fetch(`${API_BASE}/v1/admin/metrics?days=${days}`, {
    headers: adminHeaders(),
  })
  return parseJson<AdminMetricsSummary>(res, "Admin metrics")
}
