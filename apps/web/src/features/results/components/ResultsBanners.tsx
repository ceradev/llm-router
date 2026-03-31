export function ResultsBanners({
  isMock,
}: Readonly<{
  isMock: boolean
}>) {
  return (
    <>
      {isMock ? (
        <div className="mb-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          <span className="font-semibold">Offline/mock ranking.</span>{" "}
          This is fallback data (not the backend evaluator). Restore API connectivity to see real routing scores.
        </div>
      ) : null}
    </>
  )
}
