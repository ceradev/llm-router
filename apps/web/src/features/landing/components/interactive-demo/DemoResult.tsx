import { motion } from "framer-motion"

type Props = {
  modelName?: string
  description?: string
  matchScore?: number
  stretch?: boolean
}

export function DemoResult({
  modelName = "Claude 3.5 Sonnet",
  description = "High-quality planning with fast reasoning for complex tasks.",
  matchScore = 96,
  stretch = false,
}: Readonly<Props>) {
  const scoreClamped = Math.max(0, Math.min(100, matchScore))

  const rootClassName = stretch
    ? "h-full w-full flex flex-col justify-center gap-4"
    : "space-y-4"

  const articleClassName = stretch
    ? "relative overflow-hidden flex-1 min-h-0 rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-xl"
    : "relative overflow-hidden rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-xl"

  return (
    <div className={rootClassName}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-(--text-accent)">
          RESULT
        </p>
        <span className="rounded-full border border-[#3B82F6]/20 bg-[#3B82F6]/10 px-2 py-1 text-[11px] font-semibold text-(--text-muted)">
          Best match
        </span>
      </div>

      <motion.article
        initial={false}
        className={articleClassName}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background:
              "radial-gradient(circle at 20% 10%, rgba(59,130,246,0.26), transparent 55%), radial-gradient(circle at 90% 60%, rgba(14,165,233,0.20), transparent 56%), linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0))",
          }}
        />

        <div className="relative z-10">
          <p className="text-xs font-semibold text-(--text-accent)">Model</p>
          <h3 className="mt-1 text-base font-semibold tracking-tight text-(--text-primary)">
            {modelName}
          </h3>

          <p className="mt-2 text-sm leading-relaxed text-(--text-muted)">
            {description}
          </p>

          <div className={stretch ? "mt-3" : "mt-4"}>
            <div className="flex items-center justify-between gap-4">
              <p className="text-xs font-semibold text-(--text-muted)">Match score</p>
              <p className="text-xs font-semibold text-(--text-primary)">{scoreClamped}%</p>
            </div>

            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-black/5">
              <motion.div
                className="h-full rounded-full bg-linear-to-r from-[#3B82F6] to-[#0EA5E9]"
                initial={{ width: 0 }}
                animate={{ width: `${scoreClamped}%` }}
                transition={{ duration: 0.6, ease: "easeOut" }}
              />
            </div>
          </div>
        </div>
      </motion.article>
    </div>
  )
}

