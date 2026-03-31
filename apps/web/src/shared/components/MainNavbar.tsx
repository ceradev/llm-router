import type { ReactNode } from "react"

import { useI18n } from "@/contexts/I18nContext"
import { HistoryTrigger } from "@/features/history/components"
import { AppNavbar } from "./AppNavbar"
import { NavbarToolbar } from "./NavbarControls"

type Props = {
  onHistoryOpen: () => void
  historyOpen: boolean
  className?: string
  title?: ReactNode
}

export function MainNavbar({
  onHistoryOpen,
  historyOpen,
  className,
  title,
}: Readonly<Props>) {
  const { t } = useI18n()
  const appName = t("appName")
  const brandTitle = (
    <span className="inline-flex items-center gap-2">
      <span>{appName}</span>
    </span>
  )

  return (
    <AppNavbar
      className={className}
      title={title ?? brandTitle}
      rightSlot={
        <NavbarToolbar
          historySlot={
            <HistoryTrigger onClick={onHistoryOpen} expanded={historyOpen} />
          }
        />
      }
    />
  )
}

