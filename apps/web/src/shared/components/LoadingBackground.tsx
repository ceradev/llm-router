type Props = {
  colorScheme: "dark" | "light"
}

export default function LoadingBackground({
  colorScheme,
}: Readonly<Props>) {
  const isDark = colorScheme === "dark"

  return (
    <div className="absolute inset-0">
      <div
        className={["absolute inset-0", isDark ? "bg-[#05070C]" : "bg-white"].join(
          " "
        )}
      />

      {/* Subtle, centered radial gradient (very low visual noise) */}
      <div
        className="absolute inset-0"
        style={{
          background: isDark
            ? "radial-gradient(60% 55% at 50% 48%, rgba(59,130,246,0.18) 0%, rgba(59,130,246,0.08) 24%, rgba(2,6,23,0) 60%)"
            : "radial-gradient(72% 66% at 50% 50%, rgba(255,255,255,0.96) 0%, rgba(255,255,255,0.9) 30%, rgba(147,197,253,0.34) 56%, rgba(59,130,246,0.26) 78%, rgba(30,64,175,0.34) 100%)",
          opacity: 1,
        }}
        aria-hidden
      />

      {/* Gentle vignette to keep corners quiet */}
      <div
        className="absolute inset-0"
        style={{
          background: isDark
            ? "radial-gradient(90% 80% at 50% 55%, rgba(0,0,0,0) 0%, rgba(0,0,0,0.28) 75%, rgba(0,0,0,0.55) 100%)"
            : "radial-gradient(95% 85% at 50% 58%, rgba(59,130,246,0) 45%, rgba(59,130,246,0.12) 76%, rgba(30,64,175,0.24) 100%)",
          opacity: isDark ? 1 : 0.8,
        }}
        aria-hidden
      />
    </div>
  )
}

