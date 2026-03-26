import type { ReactNode } from "react"

type Props = {
  title: ReactNode
  rightSlot: ReactNode
  className?: string
}

export function AppNavbar({ title, rightSlot, className }: Readonly<Props>) {
  return (
    <header className={className}>
      <nav
        className="mx-auto flex w-full max-w-xl items-center justify-between gap-3 rounded-lg border border-(--border-subtle) bg-(--surface-glass) px-3 py-2 pl-5 shadow-(--shadow-navbar) backdrop-blur-xl sm:max-w-2xl sm:px-4 sm:py-2.5"
        aria-label="Primary"
      >
        <span className="text-lg font-semibold tracking-tight text-(--text-primary) sm:text-xl">
          {title}
        </span>
        {rightSlot}
      </nav>
    </header>
  )
}

