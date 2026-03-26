import { AnimatePresence, motion, useReducedMotion } from "framer-motion"

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="inline-block h-2 w-2 rounded-full bg-[#93C5FD]"
          initial={{ opacity: 0.35, scale: 0.9, y: 0 }}
          animate={{
            opacity: [0.35, 1, 0.35],
            scale: [0.9, 1.1, 0.9],
            y: [0, -2, 0],
          }}
          transition={{
            repeat: Infinity,
            duration: 1.05,
            ease: "easeInOut",
            delay: i * 0.18,
          }}
        />
      ))}
    </span>
  )
}

type Props = {
  text?: string
  stretch?: boolean
}

export function DemoLoading({
  text = "Analyzing...",
  stretch = false,
}: Readonly<Props>) {
  const reduceMotion = useReducedMotion() ?? false

  const rootClassName = stretch
    ? "h-full w-full flex flex-col justify-center gap-4"
    : "space-y-4"

  const cardClassName = stretch
    ? "relative overflow-hidden flex-1 min-h-0 rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-xl"
    : "relative overflow-hidden rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-xl"

  return (
    <div className={rootClassName}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-(--text-accent)">
          LOADING
        </p>
        <span className="rounded-full border border-[#3B82F6]/20 bg-[#3B82F6]/10 px-2 py-1 text-[11px] font-semibold text-(--text-muted)">
          Typing AI
        </span>
      </div>

      <div className={cardClassName}>
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background:
              "radial-gradient(circle at 30% 10%, rgba(59,130,246,0.25), transparent 55%), radial-gradient(circle at 80% 60%, rgba(14,165,233,0.18), transparent 56%)",
          }}
        />

        <div
          className={
            stretch
              ? "relative z-10 flex h-full items-center gap-3"
              : "relative z-10 flex items-center gap-3"
          }
        >
          {reduceMotion ? (
            <span className="inline-flex items-center gap-1 text-sm text-(--text-muted)">
              AI
            </span>
          ) : (
            <TypingDots />
          )}
          <p className="text-sm font-medium text-(--text-primary)">
            {text}
          </p>
        </div>

        <AnimatePresence initial={false}>
          {/* subtle shimmer */}
          {reduceMotion ? null : (
            <motion.div
              aria-hidden
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
              className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(59,130,246,0.6),transparent)]"
              style={{ transform: "translateX(-60%)" }}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

