import clsx from "clsx"

export type AppFooterProps = {
  className?: string
}

export function AppFooter({ className }: Readonly<AppFooterProps>) {
  const year = new Date().getFullYear()

  return (
    <footer
      className={clsx(
        "mt-auto border-t border-(--border-subtle) pt-4 text-[11px] text-(--text-muted) sm:pt-5 sm:text-xs",
        className
      )}
    >
      <div className="flex flex-col gap-3 sm:grid sm:grid-cols-3 sm:items-center">
        <div className="shrink-0 text-center sm:col-span-1 sm:text-left">
          © {year} LLM Router
        </div>

        <a
          href="https://ceradev.com"
          target="_blank"
          rel="noreferrer"
          className="text-center transition-colors hover:text-(--text-accent) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-subtle) rounded-sm sm:col-span-1 sm:justify-self-center"
        >
          Made by Ceradev
        </a>

        <nav className="flex flex-wrap justify-center gap-x-4 gap-y-2 sm:col-span-1 sm:justify-self-end">
          <a
            href="https://github.com/ceradev/llm-router"
            target="_blank"
            rel="noreferrer"
            className="transition-colors hover:text-(--text-accent) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-subtle) rounded-sm"
          >
            GitHub
          </a>
          <a
            href="mailto:suarezorizondocesararamis@gmail.com"
            className="transition-colors hover:text-(--text-accent) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-subtle) rounded-sm"
          >
            Feedback
          </a>
        </nav>
      </div>
    </footer>
  )
}

