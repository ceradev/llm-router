import { useEffect, useMemo, useState } from "react"

import {
  fetchAdminDashboard,
  fetchAdminMetrics,
  fetchAdminModelDetail,
  fetchAdminModels,
  fetchAdminRequests,
  runAdminModelEvaluation,
  runAdminSync,
  type AdminBatchEvaluationResult,
  type AdminDashboard,
  type AdminEvaluationMode,
  type AdminMetricsSummary,
  type AdminModelDetail,
  type AdminModelEvaluationResult,
  type AdminModelListItem,
  type AdminRequestList,
  type AdminSyncResult,
} from "@/shared/api/admin"
import { fetchProviders, type ProviderOption } from "@/shared/api/providers"

import type { AvailabilityFilter, BatchProgress, BatchStatusFilter, DropdownOption, OverviewCard } from "@/features/admin/types"
import { sleep, todayIsoDate } from "@/features/admin/utils"

export function useAdminPanel() {
  const [error, setError] = useState<string | null>(null)

  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null)
  const [metrics, setMetrics] = useState<AdminMetricsSummary | null>(null)

  const [models, setModels] = useState<AdminModelListItem[]>([])
  const [providers, setProviders] = useState<ProviderOption[]>([])
  const [providerFilter, setProviderFilter] = useState("")
  const [tierFilter, setTierFilter] = useState("")
  const [availableFilter, setAvailableFilter] = useState<AvailabilityFilter>("")
  const [evaluationStatusFilter, setEvaluationStatusFilter] = useState("")
  const [selectedRoutingKey, setSelectedRoutingKey] = useState("")
  const [selectedModelDetail, setSelectedModelDetail] = useState<AdminModelDetail | null>(null)
  const [evaluationResult, setEvaluationResult] = useState<AdminModelEvaluationResult | null>(null)
  const [evaluatingMode, setEvaluatingMode] = useState<AdminEvaluationMode | null>(null)
  const [enableImageTextV2, setEnableImageTextV2] = useState(true)
  const [strictImageTextChecks, setStrictImageTextChecks] = useState(true)
  const [enableFileTextV3, setEnableFileTextV3] = useState(false)
  const [strictFileTextChecks, setStrictFileTextChecks] = useState(true)
  const [batchMode, setBatchMode] = useState<AdminEvaluationMode>("heuristic")
  const [batchProvider, setBatchProvider] = useState("")
  const [batchStatus, setBatchStatus] = useState<BatchStatusFilter>("")
  const [batchLimit, setBatchLimit] = useState(50)
  const [batchDelayMs, setBatchDelayMs] = useState(350)
  const [batchRunning, setBatchRunning] = useState(false)
  const [batchResult, setBatchResult] = useState<AdminBatchEvaluationResult | null>(null)
  const [batchProgress, setBatchProgress] = useState<BatchProgress>({
    total: 0,
    completed: 0,
    currentRoutingKey: null,
  })
  const [batchLogs, setBatchLogs] = useState<string[]>([])

  const [requestsDate, setRequestsDate] = useState(todayIsoDate())
  const [requestsLimit, setRequestsLimit] = useState(20)
  const [requests, setRequests] = useState<AdminRequestList | null>(null)

  const [syncResult, setSyncResult] = useState<AdminSyncResult | null>(null)
  const [syncRunning, setSyncRunning] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function loadOverview() {
      try {
        const [dashboardData, metricsData] = await Promise.all([
          fetchAdminDashboard(),
          fetchAdminMetrics(7),
        ])
        if (!cancelled) {
          setDashboard(dashboardData)
          setMetrics(metricsData)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError((err as Error).message)
      }
    }
    void loadOverview()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadProviders() {
      try {
        const rows = await fetchProviders()
        if (!cancelled) setProviders(rows)
      } catch {
        // non-blocking
      }
    }
    void loadProviders()
    return () => {
      cancelled = true
    }
  }, [])

  async function handleLoadModels() {
    try {
      const rows = await fetchAdminModels({
        provider: providerFilter || undefined,
        tier: tierFilter || undefined,
        available: availableFilter === "" ? undefined : availableFilter === "true",
        evaluation_status: evaluationStatusFilter || undefined,
      })
      setModels(rows)
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function handleLoadModelDetail() {
    if (!selectedRoutingKey.trim()) return
    try {
      const detail = await fetchAdminModelDetail(selectedRoutingKey.trim())
      setSelectedModelDetail(detail)
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function handleRunModelEvaluation(mode: AdminEvaluationMode) {
    if (!selectedRoutingKey.trim()) return
    setEvaluatingMode(mode)
    try {
      const result = await runAdminModelEvaluation(selectedRoutingKey.trim(), mode, {
        enableImageTextV2,
        strictImageTextChecks,
        enableFileTextV3,
        strictFileTextChecks,
      })
      setEvaluationResult(result)
      await handleLoadModelDetail()
      await handleLoadModels()
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setEvaluatingMode(null)
    }
  }

  async function handleLoadRequests() {
    try {
      const response = await fetchAdminRequests(requestsDate, requestsLimit)
      setRequests(response)
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function handleRunSync() {
    setSyncRunning(true)
    try {
      const result = await runAdminSync()
      setSyncResult(result)
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSyncRunning(false)
    }
  }

  async function handleRunBatchEvaluation() {
    setBatchResult(null)
    setBatchLogs([])
    setBatchRunning(true)
    try {
      const candidates = await fetchAdminModels({
        provider: batchProvider || undefined,
        evaluation_status: batchStatus || undefined,
      })
      const selected = candidates.slice(0, Math.max(1, batchLimit))
      setBatchProgress({ total: selected.length, completed: 0, currentRoutingKey: null })

      let succeeded = 0
      let failed = 0
      let skipped = 0
      const benchmarkStatusCounts: Record<string, number> = {}
      const skipReasonCounts: Record<string, number> = {}
      const skippedModels: Array<{ routing_key: string; reason: string }> = []
      const errorMessages: string[] = []

      for (let index = 0; index < selected.length; index += 1) {
        const row = selected[index]
        setBatchProgress({
          total: selected.length,
          completed: index,
          currentRoutingKey: row.routing_key,
        })
        setBatchLogs((prev) => [...prev.slice(-80), `[${index + 1}/${selected.length}] ${row.routing_key} - running ${batchMode}`])
        try {
          const evaluation = await runAdminModelEvaluation(row.routing_key, batchMode, {
            enableImageTextV2,
            strictImageTextChecks,
            enableFileTextV3,
            strictFileTextChecks,
          })
          const statusKey = evaluation.benchmark_status
          benchmarkStatusCounts[statusKey] = (benchmarkStatusCounts[statusKey] ?? 0) + 1
          if (statusKey === "skipped_unsupported") {
            skipped += 1
            const reason = evaluation.skip_reason ?? "unknown"
            skipReasonCounts[reason] = (skipReasonCounts[reason] ?? 0) + 1
            skippedModels.push({ routing_key: row.routing_key, reason })
          } else {
            succeeded += 1
          }
          const skipSuffix = evaluation.skip_reason ? ` (${evaluation.skip_reason})` : ""
          setBatchLogs((prev) => [...prev.slice(-80), `[${index + 1}/${selected.length}] ${row.routing_key} - ${statusKey}${skipSuffix}`])
        } catch (err) {
          failed += 1
          const message = `${row.routing_key}: ${(err as Error).message}`
          errorMessages.push(message)
          setBatchLogs((prev) => [...prev.slice(-80), `[${index + 1}/${selected.length}] ${message}`])
        }
        if (index < selected.length - 1 && batchDelayMs > 0) await sleep(batchDelayMs)
      }

      setBatchProgress({ total: selected.length, completed: selected.length, currentRoutingKey: null })
      setBatchResult({
        mode: batchMode,
        matched_models: candidates.length,
        processed_models: selected.length,
        succeeded,
        failed,
        skipped,
        benchmark_status_counts: benchmarkStatusCounts,
        skip_reason_counts: skipReasonCounts,
        skipped_models: skippedModels.slice(0, 100),
        error_messages: errorMessages.slice(0, 20),
      })
      await handleLoadModels()
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBatchRunning(false)
    }
  }

  const overviewCards = useMemo<OverviewCard[]>(
    () => [
      { label: "Total Models", value: dashboard?.total_models ?? "-" },
      { label: "Total Providers", value: dashboard?.total_providers ?? "-" },
      { label: "Requests Today", value: dashboard?.requests_today ?? "-" },
      {
        label: "Success Rate",
        value: dashboard ? `${(dashboard.success_rate * 100).toFixed(1)}%` : "-",
      },
    ],
    [dashboard],
  )

  const providerOptions = useMemo<DropdownOption[]>(
    () => [
      { value: "", label: "provider: all" },
      ...providers.map((provider) => ({
        value: provider.slug,
        label: provider.display_name,
      })),
    ],
    [providers],
  )

  const availabilityOptions: DropdownOption[] = [
    { value: "", label: "availability: all" },
    { value: "true", label: "available" },
    { value: "false", label: "unavailable" },
  ]

  const tierOptions: DropdownOption[] = [
    { value: "", label: "tier: all" },
    { value: "premium", label: "premium" },
    { value: "alternative", label: "alternative" },
    { value: "free", label: "free" },
  ]

  const evaluationOptions: DropdownOption[] = [
    { value: "", label: "status: all" },
    { value: "cataloged", label: "cataloged" },
    { value: "provisional", label: "provisional" },
    { value: "verified", label: "verified" },
    { value: "rejected", label: "rejected" },
  ]

  return {
    error,
    overviewCards,
    metrics,
    models,
    providerOptions,
    tierOptions,
    availabilityOptions,
    evaluationOptions,
    providerFilter,
    tierFilter,
    availableFilter,
    evaluationStatusFilter,
    selectedRoutingKey,
    selectedModelDetail,
    evaluationResult,
    evaluatingMode,
    enableImageTextV2,
    strictImageTextChecks,
    enableFileTextV3,
    strictFileTextChecks,
    batchMode,
    batchProvider,
    batchStatus,
    batchLimit,
    batchDelayMs,
    batchRunning,
    batchResult,
    batchProgress,
    batchLogs,
    requestsDate,
    requestsLimit,
    requests,
    syncRunning,
    syncResult,
    setProviderFilter,
    setTierFilter,
    setAvailableFilter,
    setEvaluationStatusFilter,
    setSelectedRoutingKey,
    setEnableImageTextV2,
    setStrictImageTextChecks,
    setEnableFileTextV3,
    setStrictFileTextChecks,
    setBatchMode,
    setBatchProvider,
    setBatchStatus,
    setBatchLimit,
    setBatchDelayMs,
    setRequestsDate,
    setRequestsLimit,
    handleLoadModels,
    handleLoadModelDetail,
    handleRunModelEvaluation,
    handleRunBatchEvaluation,
    handleLoadRequests,
    handleRunSync,
  }
}
