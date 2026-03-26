import { motion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"
import type { DecisionMetricKey, ModelDecision } from "@/features/results/types"

const METRICS: DecisionMetricKey[] = [
  "reasoning",
  "speed",
  "costEfficiency",
  "contextWindow",
]

function metricLabel(t: (k: any) => string, key: DecisionMetricKey) {
  if (key === "reasoning") return t("benchmarkReasoning")
  if (key === "speed") return t("benchmarkSpeed")
  if (key === "costEfficiency") return t("benchmarkCostEfficiency")
  return t("benchmarkContextWindow")
}

function Bar({
  value,
  tone,
}: Readonly<{ value: number; tone: "primary" | "muted" }>) {
  const v = Math.max(0, Math.min(100, value))
  const track =
    "h-2.5 w-full overflow-hidden rounded-full bg-black/10 dark:bg-white/10"
  const fill =
    tone === "primary"
      ? "h-full rounded-full bg-linear-to-r from-[#3B82F6] via-[#1D4ED8] to-[#0EA5E9]"
      : "h-full rounded-full bg-white/30"

  return (
    <div className={track} aria-hidden>
      <div className={fill} style={{ width: `${v}%` }} />
    </div>
  )
}

function formatTokens(tokens?: number) {
  if (!tokens || !Number.isFinite(tokens)) return undefined
  if (tokens >= 1_000_000) return `${Math.round(tokens / 100_000) / 10}M`
  if (tokens >= 1000) return `${Math.round(tokens / 100) / 10}k`
  return `${Math.round(tokens)}`
}

export function BenchmarkChart({
  models,
}: Readonly<{
  models: ModelDecision[]
}>) {
  const { t } = useI18n()

  if (models.length === 0) return null

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-5 shadow-(--shadow-elevated) backdrop-blur-xl sm:p-6"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-(--text-muted)">
            {t("benchmark")}
          </p>
          <h3 className="mt-2 text-lg font-semibold text-(--text-primary) sm:text-xl">
            {t("benchmarkTitle")}
          </h3>
          <p className="mt-1 text-sm text-(--text-muted)">
            {t("benchmarkSubtitle")}
          </p>
        </div>
      </div>

      <div className="mt-5 overflow-x-auto">
        <table className="min-w-[720px] w-full border-separate border-spacing-0">
          <thead>
            <tr>
              <th
                scope="col"
                className="sticky left-0 z-10 w-52 bg-(--surface-glass) px-3 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-(--text-muted) backdrop-blur-xl"
              >
                {t("benchmarkMetric")}
              </th>
              {models.map((m, idx) => (
                <th
                  key={m.id ?? `${m.name}-${idx}`}
                  scope="col"
                  className="px-3 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-(--text-muted)"
                >
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold text-(--text-primary)">
                      {m.name}
                    </p>
                    <p className="truncate text-[11px] font-medium text-(--text-muted)">
                      {m.provider}
                    </p>
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {METRICS.map((key) => (
              <tr key={key}>
                <th
                  scope="row"
                  className="sticky left-0 z-10 border-t border-(--border-subtle) bg-(--surface-glass) px-3 py-4 text-left text-sm font-medium text-(--text-primary) backdrop-blur-xl"
                >
                  <div className="flex flex-col">
                    <span>{metricLabel(t, key)}</span>
                    {key === "contextWindow" && (
                      <span className="mt-0.5 text-xs font-normal text-(--text-muted)">
                        {t("benchmarkContextWindowHint")}
                      </span>
                    )}
                  </div>
                </th>

                {models.map((m, idx) => {
                  const value = m.metrics?.[key] ?? 0
                  const tone = idx === 0 ? "primary" : "muted"
                  const tokenLabel =
                    key === "contextWindow" ? formatTokens(m.contextWindowTokens) : undefined

                  return (
                    <td
                      key={`${m.id ?? m.name}-${key}`}
                      className="border-t border-(--border-subtle) px-3 py-4 align-top"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold tabular-nums text-(--text-primary)">
                          {Math.round(value)}
                        </p>
                        {tokenLabel && (
                          <p className="text-xs font-medium tabular-nums text-(--text-muted)">
                            {tokenLabel}
                          </p>
                        )}
                      </div>
                      <div className="mt-2">
                        <Bar value={value} tone={tone} />
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.section>
  )
}

