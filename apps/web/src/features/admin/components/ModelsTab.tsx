import type {
  AdminBatchEvaluationResult,
  AdminEvaluationMode,
  AdminModelDetail,
  AdminModelEvaluationResult,
  AdminModelListItem,
} from "@/shared/api/admin"

import { actionButtonClass, fieldClass } from "@/features/admin/constants"
import { type AvailabilityFilter, type BatchProgress, type BatchStatusFilter, type DropdownOption } from "@/features/admin/types"
import { modelStatusBadgeClass } from "@/features/admin/utils"

import { CustomDropdown } from "./CustomDropdown"

function humanizeReason(reason: string): string {
  return reason.replaceAll("_", " ").replaceAll(":", " / ")
}

function BatchResultSummary({ batchResult }: Readonly<{ batchResult: AdminBatchEvaluationResult }>) {
  const skipReasonEntries = Object.entries(batchResult.skip_reason_counts ?? {})
  const failedReasonEntries = Object.entries(batchResult.failed_reason_counts ?? {})

  return (
    <div className="mt-3 space-y-3">
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-2 py-1 text-emerald-200">
          completed: {batchResult.succeeded}
        </span>
        <span className="rounded-full border border-red-400/30 bg-red-500/10 px-2 py-1 text-red-200">
          failed: {batchResult.failed}
        </span>
        <span className="rounded-full border border-amber-400/30 bg-amber-500/10 px-2 py-1 text-amber-200">
          skipped: {batchResult.skipped}
        </span>
      </div>

      {failedReasonEntries.length > 0 ? (
        <div className="rounded-xl border border-(--border-subtle) bg-black/20 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-(--text-muted)">failed reasons</p>
          <div className="flex flex-wrap gap-2">
            {failedReasonEntries.map(([reason, count]) => (
              <span key={reason} className="rounded-full border border-red-400/30 bg-red-500/10 px-2 py-1 text-[11px] text-red-200">
                {humanizeReason(reason)}: {count}
              </span>
            ))}
          </div>
          {(batchResult.failed_models?.length ?? 0) > 0 ? (
            <div className="mt-2 max-h-24 overflow-auto text-xs text-(--text-muted)">
              {batchResult.failed_models?.slice(0, 8).map((item) => (
                <div key={`${item.routing_key}-${item.reason}`}>
                  {item.routing_key} - {humanizeReason(item.reason)}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {skipReasonEntries.length > 0 ? (
        <div className="rounded-xl border border-(--border-subtle) bg-black/20 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-(--text-muted)">skip reasons</p>
          <div className="flex flex-wrap gap-2">
            {skipReasonEntries.map(([reason, count]) => (
              <span key={reason} className="rounded-full border border-amber-400/30 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-200">
                {humanizeReason(reason)}: {count}
              </span>
            ))}
          </div>
          {(batchResult.skipped_models?.length ?? 0) > 0 ? (
            <div className="mt-2 max-h-24 overflow-auto text-xs text-(--text-muted)">
              {batchResult.skipped_models?.slice(0, 8).map((item) => (
                <div key={`${item.routing_key}-${item.reason}`}>
                  {item.routing_key} - {humanizeReason(item.reason)}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <pre className="overflow-auto rounded-xl border border-(--border-subtle) bg-black/20 p-3 text-xs text-(--text-muted)">
        {JSON.stringify(batchResult, null, 2)}
      </pre>
    </div>
  )
}

export function ModelsTab({
  providerFilter,
  tierFilter,
  availableFilter,
  evaluationStatusFilter,
  providerOptions,
  tierOptions,
  availabilityOptions,
  evaluationOptions,
  selectedRoutingKey,
  evaluatingMode,
  enableImageTextV2,
  strictImageTextChecks,
  enableFileTextV3,
  strictFileTextChecks,
  evaluationResult,
  selectedModelDetail,
  models,
  onProviderFilter,
  onTierFilter,
  onAvailableFilter,
  onEvaluationStatusFilter,
  onSelectedRoutingKey,
  onEnableImageTextV2,
  onStrictImageTextChecks,
  onEnableFileTextV3,
  onStrictFileTextChecks,
  onLoadModels,
  onLoadModelDetail,
  onRunHeuristic,
  onRunLive,
  batchMode,
  batchProvider,
  batchStatus,
  batchLimit,
  batchRunning,
  batchResult,
  batchDelayMs,
  batchProgress,
  batchLogs,
  onBatchMode,
  onBatchProvider,
  onBatchStatus,
  onBatchLimit,
  onBatchDelayMs,
  onRunBatch,
}: Readonly<{
  providerFilter: string
  tierFilter: string
  availableFilter: AvailabilityFilter
  evaluationStatusFilter: string
  providerOptions: DropdownOption[]
  tierOptions: DropdownOption[]
  availabilityOptions: DropdownOption[]
  evaluationOptions: DropdownOption[]
  selectedRoutingKey: string
  evaluatingMode: AdminEvaluationMode | null
  enableImageTextV2: boolean
  strictImageTextChecks: boolean
  enableFileTextV3: boolean
  strictFileTextChecks: boolean
  evaluationResult: AdminModelEvaluationResult | null
  selectedModelDetail: AdminModelDetail | null
  models: AdminModelListItem[]
  onProviderFilter: (value: string) => void
  onTierFilter: (value: string) => void
  onAvailableFilter: (value: AvailabilityFilter) => void
  onEvaluationStatusFilter: (value: string) => void
  onSelectedRoutingKey: (value: string) => void
  onEnableImageTextV2: (checked: boolean) => void
  onStrictImageTextChecks: (checked: boolean) => void
  onEnableFileTextV3: (checked: boolean) => void
  onStrictFileTextChecks: (checked: boolean) => void
  onLoadModels: () => void
  onLoadModelDetail: () => void
  onRunHeuristic: () => void
  onRunLive: () => void
  batchMode: AdminEvaluationMode
  batchProvider: string
  batchStatus: BatchStatusFilter
  batchLimit: number
  batchRunning: boolean
  batchResult: AdminBatchEvaluationResult | null
  batchDelayMs: number
  batchProgress: BatchProgress
  batchLogs: string[]
  onBatchMode: (value: AdminEvaluationMode) => void
  onBatchProvider: (value: string) => void
  onBatchStatus: (value: BatchStatusFilter) => void
  onBatchLimit: (value: number) => void
  onBatchDelayMs: (value: number) => void
  onRunBatch: () => void
}>) {
  const isSkippedUnsupported = evaluationResult?.benchmark_status === "skipped_unsupported"
  let evaluationOutcomeLabel = "failed"
  if (isSkippedUnsupported)
    evaluationOutcomeLabel = "skipped"
  else if (evaluationResult?.passed)
    evaluationOutcomeLabel = "passed"

  const batchModeOptions: DropdownOption[] = [
    { value: "heuristic", label: "mode: heuristic" },
    { value: "live", label: "mode: live" },
  ]
  const batchStatusOptions: DropdownOption[] = [
    { value: "", label: "batch status: all" },
    { value: "cataloged", label: "cataloged" },
    { value: "provisional", label: "provisional" },
    { value: "verified", label: "verified" },
    { value: "rejected", label: "rejected" },
    { value: "deprecated", label: "deprecated" },
  ]
  return (
    <section className="space-y-4">
      <div className="space-y-4">
        <div className="relative z-60 overflow-visible rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-md">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            Filters
          </p>
          <div className="flex flex-wrap gap-2">
            <CustomDropdown value={providerFilter} options={providerOptions} onChange={onProviderFilter} placeholder="provider" />
            <CustomDropdown value={tierFilter} options={tierOptions} onChange={onTierFilter} placeholder="tier" />
            <CustomDropdown
              value={availableFilter}
              options={availabilityOptions}
              onChange={(value) => onAvailableFilter(value as AvailabilityFilter)}
              placeholder="availability"
            />
            <CustomDropdown
              value={evaluationStatusFilter}
              options={evaluationOptions}
              onChange={onEvaluationStatusFilter}
              placeholder="status"
            />
            <button type="button" className={actionButtonClass} onClick={onLoadModels}>
              Load Models
            </button>
          </div>
        </div>

        <div className="relative z-10 rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-md">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            Model Detail
          </p>
          <div className="flex flex-wrap gap-2">
            <input
              value={selectedRoutingKey}
              onChange={(event) => onSelectedRoutingKey(event.target.value)}
              placeholder="routing_key for detail"
              className={`${fieldClass} min-w-80 flex-1`}
            />
            <button type="button" className={actionButtonClass} onClick={onLoadModelDetail}>
              Get Model Detail
            </button>
            <button type="button" className={actionButtonClass} onClick={onRunHeuristic} disabled={evaluatingMode !== null}>
              {evaluatingMode === "heuristic" ? "Running heuristic..." : "Run Heuristic (provisional)"}
            </button>
            <button type="button" className={actionButtonClass} onClick={onRunLive} disabled={evaluatingMode !== null}>
              {evaluatingMode === "live" ? "Running live..." : "Run Live (verify)"}
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-(--text-muted)">
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={enableImageTextV2} onChange={(event) => onEnableImageTextV2(event.target.checked)} />
              <span>enable image -&gt; text v2</span>
            </label>
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={strictImageTextChecks} onChange={(event) => onStrictImageTextChecks(event.target.checked)} />
              <span>strict image checks</span>
            </label>
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={enableFileTextV3} onChange={(event) => onEnableFileTextV3(event.target.checked)} />
              <span>enable file -&gt; text v3</span>
            </label>
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={strictFileTextChecks} onChange={(event) => onStrictFileTextChecks(event.target.checked)} />
              <span>strict file checks</span>
            </label>
          </div>
        </div>

        <div className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-md">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            Batch Evaluation
          </p>
          <div className="flex flex-wrap items-end gap-2">
            <CustomDropdown value={batchMode} options={batchModeOptions} onChange={(value) => onBatchMode(value as AdminEvaluationMode)} placeholder="mode" />
            <CustomDropdown value={batchProvider} options={providerOptions} onChange={onBatchProvider} placeholder="provider" />
            <CustomDropdown
              value={batchStatus}
              options={batchStatusOptions}
              onChange={(value) => onBatchStatus(value as BatchStatusFilter)}
              placeholder="status"
            />
            <input
              type="number"
              min={1}
              max={5000}
              value={batchLimit}
              onChange={(event) => onBatchLimit(Number(event.target.value))}
              className={`${fieldClass} w-28`}
            />
            <input
              type="number"
              min={0}
              max={10000}
              value={batchDelayMs}
              onChange={(event) => onBatchDelayMs(Number(event.target.value))}
              className={`${fieldClass} w-32`}
              title="Delay between models (ms)"
            />
            <button type="button" className={actionButtonClass} onClick={onRunBatch} disabled={batchRunning}>
              {batchRunning ? "Running batch..." : "Run Batch"}
            </button>
          </div>
          <p className="mt-2 text-xs text-(--text-muted)">
            Evalua en lote por proveedor/estado y cantidad maxima. Delay (ms) aplica entre modelos.
          </p>
          <p className="mt-1 text-xs text-(--text-muted)">
            progreso: {batchProgress.completed}/{batchProgress.total}
            {batchProgress.currentRoutingKey ? ` - actual: ${batchProgress.currentRoutingKey}` : ""}
          </p>
          {batchLogs.length > 0 ? (
            <div className="mt-2 max-h-40 overflow-auto rounded-xl border border-(--border-subtle) bg-black/20 p-2 text-xs text-(--text-muted)">
              {batchLogs.map((line, index) => (
                <div key={`${line}-${index}`}>{line}</div>
              ))}
            </div>
          ) : null}
          {batchResult ? <BatchResultSummary batchResult={batchResult} /> : null}
        </div>

        {evaluationResult ? (
          <article className="rounded-xl border border-(--border-subtle) bg-black/20 p-3">
            <p className="text-sm text-(--text-primary)">
              Last evaluation: <span className="font-semibold">{evaluationResult.mode}</span> {"->"}{" "}
              <span className="font-semibold">{evaluationResult.evaluation_status_after}</span>
            </p>
            <p className="text-xs text-(--text-muted)">
              benchmark #{evaluationResult.benchmark_run_id} ({evaluationResult.benchmark_status},{" "}
              {evaluationResult.benchmark_scope}) - {evaluationOutcomeLabel}
            </p>
            {evaluationResult.cases.length > 0 ? (
              <div className="mt-2 space-y-1">
                {evaluationResult.cases.map((caseRow) => (
                  <div key={caseRow.id} className="text-xs text-(--text-muted)">
                    {(() => {
                      let caseLabel = "fail"
                      if (isSkippedUnsupported && !caseRow.ok)
                        caseLabel = "skipped"
                      else if (caseRow.ok)
                        caseLabel = "ok"
                      return (
                        <>
                          <span className="font-semibold text-(--text-primary)">{caseRow.id}</span>: {caseLabel} - {caseRow.detail}
                        </>
                      )
                    })()}
                  </div>
                ))}
              </div>
            ) : null}
          </article>
        ) : null}
        {selectedModelDetail ? (
          <article className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-md">
            <pre className="overflow-auto rounded-xl border border-(--border-subtle) bg-black/20 p-3 text-xs text-(--text-muted)">
              {JSON.stringify(selectedModelDetail, null, 2)}
            </pre>
            <p className="mt-2 text-xs text-(--text-muted)">
              modalities: in [{selectedModelDetail.input_modalities.join(", ") || "-"}], out [{selectedModelDetail.output_modalities.join(", ") || "-"}]
            </p>
          </article>
        ) : null}
      </div>

      <div className="overflow-auto rounded-2xl border border-(--border-subtle) bg-(--surface-glass) shadow-(--shadow-card) backdrop-blur-md">
        <table className="w-full text-sm text-(--text-primary)">
          <thead className="bg-black/10 text-(--text-muted)">
            <tr>
              <th className="p-3 text-left">routing_key</th>
              <th className="p-3 text-left">provider</th>
              <th className="p-3 text-left">tier</th>
              <th className="p-3 text-left">available</th>
              <th className="p-3 text-left">status</th>
            </tr>
          </thead>
          <tbody>
            {models.map((row) => (
              <tr key={row.routing_key} className="border-t border-(--border-subtle)">
                <td className="p-3">{row.routing_key}</td>
                <td className="p-3">{row.provider}</td>
                <td className="p-3">{row.tier}</td>
                <td className="p-3">{row.is_available ? "yes" : "no"}</td>
                <td className="p-3">
                  <span
                    className={`rounded-full border px-2 py-1 text-[11px] uppercase tracking-wide ${modelStatusBadgeClass(row.evaluation_status)}`}
                  >
                    {row.evaluation_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
