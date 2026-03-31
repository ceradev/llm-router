import { useEffect, useMemo, useState } from "react"

import { tabs } from "@/features/admin/constants"
import { ModelsTab, OverviewTab, RequestsTab, SyncTab } from "@/features/admin/components"
import { useAdminPanel } from "@/features/admin/hooks"
import type { AdminTab } from "@/features/admin/types"
import { clearStoredAdminKey, getStoredAdminKey, setStoredAdminKey, verifyAdminKey } from "@/shared/api/admin"

export default function AdminPanel() {
  const [tab, setTab] = useState<AdminTab>("overview")
  const vm = useAdminPanel()
  const [adminKey, setAdminKey] = useState("")
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)
  const [verifying, setVerifying] = useState(false)

  useEffect(() => {
    const stored = getStoredAdminKey()
    if (stored) setAdminKey(stored)
    setAuthModalOpen(!stored)
  }, [])

  useEffect(() => {
    if (vm.authRequired) {
      setAuthModalOpen(true)
      setAuthError("Clave incorrecta o caducada. Vuelve a introducirla.")
      setAdminKey("")
    }
  }, [vm.authRequired])

  const adminKeyPresent = useMemo(() => Boolean(adminKey.trim()), [adminKey])

  const tabButtonClass = (isActive: boolean): string =>
    [
      "rounded-xl border px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)",
      isActive
        ? "border-(--text-accent) bg-(--surface-glass-hover) text-(--text-primary)"
        : "border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) hover:text-(--text-primary) hover:bg-(--surface-glass-hover)",
    ].join(" ")

  async function handleAdminKeySubmit() {
    const normalized = adminKey.trim()
    if (!normalized) {
      setAuthError("Introduce la clave de administrador")
      return
    }
    setVerifying(true)
    setAuthError(null)
    try {
      const result = await verifyAdminKey(normalized)
      if (!result.ok) {
        setAuthError(result.message)
        return
      }
      setStoredAdminKey(normalized)
      setAuthError(null)
      setAuthModalOpen(false)
      await vm.reloadOverview()
    } catch (e) {
      setAuthError((e as Error).message)
    } finally {
      setVerifying(false)
    }
  }

  function handleAdminKeyLogout() {
    clearStoredAdminKey()
    setAdminKey("")
    setAuthError(null)
    setAuthModalOpen(true)
  }

  return (
    <div className="relative z-10 mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-4 pb-14 pt-8 sm:px-6 sm:pt-10">
      {authModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div className="relative w-full max-w-lg rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-6 shadow-(--shadow-card) backdrop-blur-md">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-(--text-accent)">
              Admin access
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-(--text-primary)">Acceso al panel</h2>
            <p className="mt-2 text-sm text-(--text-muted)">
              Introduce la misma clave que configuraste como <code className="text-(--text-accent)">ADMIN_API_KEY</code> en el
              servidor. Se comprueba contra la API antes de desbloquear.
            </p>

            <form
              className="mt-5"
              onSubmit={(e) => {
                e.preventDefault()
                void handleAdminKeySubmit()
              }}
            >
              <label
                htmlFor="admin-key"
                className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-(--text-muted)"
              >
                Contraseña de administrador
              </label>
              <input
                id="admin-key"
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                type="password"
                autoComplete="current-password"
                placeholder="La clave no se guarda hasta que sea correcta"
                disabled={verifying}
                className="w-full rounded-xl border border-(--border-subtle) bg-black/20 px-4 py-3 text-sm text-(--text-primary) outline-none focus:border-(--text-accent) disabled:opacity-60"
              />
              {authError ? (
                <p className="mt-2 text-sm text-red-300">{authError}</p>
              ) : null}
            </form>

            <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => {
                  clearStoredAdminKey()
                  setAuthError(null)
                  globalThis.window.location.assign("/")
                }}
                disabled={verifying}
                className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-4 py-2 text-sm font-medium text-(--text-muted) hover:bg-(--surface-glass-hover) hover:text-(--text-primary) disabled:opacity-60"
              >
                Salir
              </button>
              <button
                type="button"
                onClick={() => void handleAdminKeySubmit()}
                disabled={verifying}
                className="rounded-xl border border-(--text-accent) bg-(--surface-glass-hover) px-4 py-2 text-sm font-semibold text-(--text-primary) hover:brightness-110 disabled:opacity-60"
              >
                {verifying ? "Comprobando…" : "Desbloquear"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

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
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <div className="text-xs text-(--text-muted)">
            Status:{" "}
            <span className={adminKeyPresent ? "text-emerald-300" : "text-amber-300"}>
              {adminKeyPresent ? "unlocked" : "locked"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setAuthModalOpen(true)}
              className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-3 py-2 text-xs font-medium text-(--text-muted) hover:bg-(--surface-glass-hover) hover:text-(--text-primary)"
            >
              Change key
            </button>
            <button
              type="button"
              onClick={handleAdminKeyLogout}
              className="rounded-xl border border-(--border-subtle) bg-(--surface-glass) px-3 py-2 text-xs font-medium text-(--text-muted) hover:bg-(--surface-glass-hover) hover:text-(--text-primary)"
            >
              Logout
            </button>
          </div>
        </div>
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
