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

  return (
    <AppNavbar
      className={className}
      title={title ?? t("appName")}
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

