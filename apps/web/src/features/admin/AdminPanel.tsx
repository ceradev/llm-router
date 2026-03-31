import { useState } from "react"

import { tabs } from "@/features/admin/constants"
import { ModelsTab, OverviewTab, RequestsTab, SyncTab } from "@/features/admin/components"
import { useAdminPanel } from "@/features/admin/hooks"
import type { AdminTab } from "@/features/admin/types"

export default function AdminPanel() {
  const [tab, setTab] = useState<AdminTab>("overview")
  const vm = useAdminPanel()

  const tabButtonClass = (isActive: boolean): string =>
    [
      "rounded-xl border px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)",
      isActive
        ? "border-(--text-accent) bg-(--surface-glass-hover) text-(--text-primary)"
        : "border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) hover:text-(--text-primary) hover:bg-(--surface-glass-hover)",
    ].join(" ")

  return (
    <div className="relative z-10 mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-4 pb-14 pt-8 sm:px-6 sm:pt-10">
      <header className="mb-6 rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-5 shadow-(--shadow-card) backdrop-blur-md">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-(--text-accent)">
          Administration
        </p>
        <h1 className="mt-2 bg-linear-to-r from-(--headline-from) via-(--headline-via) to-(--headline-to) bg-clip-text text-3xl font-semibold text-transparent sm:text-4xl">
          Router Control Panel
        </h1>
        <p className="mt-2 text-sm text-(--text-muted)">
          Vista operativa para monitorear catálogo, requests y sincronización manual.
        </p>
      </header>

      <div className="mb-6 flex flex-wrap gap-2">
        {tabs.map((item) => (
          <button
            key={item.key}
            type="button"
            className={tabButtonClass(tab === item.key)}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {vm.error ? (
        <div className="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">
          {vm.error}
        </div>
      ) : null}

      {tab === "overview" ? <OverviewTab overviewCards={vm.overviewCards} metrics={vm.metrics} /> : null}

      {tab === "models" ? (
        <ModelsTab
          providerFilter={vm.providerFilter}
          tierFilter={vm.tierFilter}
          availableFilter={vm.availableFilter}
          evaluationStatusFilter={vm.evaluationStatusFilter}
          providerOptions={vm.providerOptions}
          tierOptions={vm.tierOptions}
          availabilityOptions={vm.availabilityOptions}
          evaluationOptions={vm.evaluationOptions}
          selectedRoutingKey={vm.selectedRoutingKey}
          evaluatingMode={vm.evaluatingMode}
          enableImageTextV2={vm.enableImageTextV2}
          strictImageTextChecks={vm.strictImageTextChecks}
          enableFileTextV3={vm.enableFileTextV3}
          strictFileTextChecks={vm.strictFileTextChecks}
          evaluationResult={vm.evaluationResult}
          selectedModelDetail={vm.selectedModelDetail}
          models={vm.models}
          onProviderFilter={vm.setProviderFilter}
          onTierFilter={vm.setTierFilter}
          onAvailableFilter={vm.setAvailableFilter}
          onEvaluationStatusFilter={vm.setEvaluationStatusFilter}
          onSelectedRoutingKey={vm.setSelectedRoutingKey}
          onEnableImageTextV2={vm.setEnableImageTextV2}
          onStrictImageTextChecks={vm.setStrictImageTextChecks}
          onEnableFileTextV3={vm.setEnableFileTextV3}
          onStrictFileTextChecks={vm.setStrictFileTextChecks}
          onLoadModels={() => void vm.handleLoadModels()}
          onLoadModelDetail={() => void vm.handleLoadModelDetail()}
          onRunHeuristic={() => void vm.handleRunModelEvaluation("heuristic")}
          onRunLive={() => void vm.handleRunModelEvaluation("live")}
          batchMode={vm.batchMode}
          batchProvider={vm.batchProvider}
          batchStatus={vm.batchStatus}
          batchLimit={vm.batchLimit}
          batchDelayMs={vm.batchDelayMs}
          batchRunning={vm.batchRunning}
          batchResult={vm.batchResult}
          batchProgress={vm.batchProgress}
          batchLogs={vm.batchLogs}
          onBatchMode={vm.setBatchMode}
          onBatchProvider={vm.setBatchProvider}
          onBatchStatus={vm.setBatchStatus}
          onBatchLimit={vm.setBatchLimit}
          onBatchDelayMs={vm.setBatchDelayMs}
          onRunBatch={() => void vm.handleRunBatchEvaluation()}
        />
      ) : null}

      {tab === "requests" ? (
        <RequestsTab
          requestsDate={vm.requestsDate}
          requestsLimit={vm.requestsLimit}
          requests={vm.requests}
          onRequestsDate={vm.setRequestsDate}
          onRequestsLimit={vm.setRequestsLimit}
          onLoadRequests={() => void vm.handleLoadRequests()}
        />
      ) : null}

      {tab === "sync" ? (
        <SyncTab
          syncRunning={vm.syncRunning}
          syncResult={vm.syncResult}
          onRunSync={() => void vm.handleRunSync()}
        />
      ) : null}

    </div>
  )
}
