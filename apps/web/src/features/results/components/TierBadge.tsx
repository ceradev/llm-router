import { motion } from "framer-motion"

type TierBadgeProps = {
  tier: string | undefined
  className?: string
}

const TIER_CONFIGS: Record<string, { label: string; className: string }> = {
  tier1_verified: {
    label: "Verified",
    className:
      "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  },
  tier2_provisional: {
    label: "Provisional",
    className:
      "bg-slate-500/10 text-slate-400 border border-slate-500/20",
  },
}

export function TierBadge({ tier, className = "" }: Readonly<TierBadgeProps>) {
  if (!tier) return null
  const config = TIER_CONFIGS[tier]
  if (!config) return null

  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${config.className} ${className}`}
    >
      {tier === "tier1_verified" ? (
        <svg
          aria-hidden
          className="h-2.5 w-2.5"
          viewBox="0 0 12 12"
          fill="currentColor"
        >
          <path d="M6 0L1 2.5v4C1 9.1 3.2 11.5 6 12c2.8-.5 5-2.9 5-5.5v-4L6 0z" />
        </svg>
      ) : null}
      {config.label}
    </motion.span>
  )
}
