import { motion } from "framer-motion"

type Props = {
  prompt: string
  stretch?: boolean
}

export function DemoInput({ prompt, stretch = false }: Readonly<Props>) {
  const rootClassName = stretch
    ? "h-full w-full flex flex-col justify-center gap-4"
    : "space-y-4"

  const textareaWrapperClassName = stretch
    ? "flex-1 min-h-0 rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-xl"
    : "rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 shadow-(--shadow-card) backdrop-blur-xl"

  const textareaClassName = stretch
    ? "h-full resize-none bg-transparent text-sm leading-relaxed text-(--text-primary) outline-none placeholder:text-(--text-muted)"
    : "w-full resize-none bg-transparent text-sm leading-relaxed text-(--text-primary) outline-none placeholder:text-(--text-muted)"

  return (
    <motion.div
      className={rootClassName}
      initial={false}
      animate={{}}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-(--text-accent)">
          INPUT
        </p>
        <span className="rounded-full border border-[#3B82F6]/20 bg-[#3B82F6]/10 px-2 py-1 text-[11px] font-semibold text-(--text-muted)">
          Auto-run
        </span>
      </div>

      <div className={textareaWrapperClassName}>
        <label htmlFor="demo-prompt" className="sr-only">
          Demo prompt
        </label>
        <textarea
          id="demo-prompt"
          value={prompt}
          readOnly
          rows={stretch ? 1 : 3}
          className={textareaClassName}
        />
      </div>
    </motion.div>
  )
}

