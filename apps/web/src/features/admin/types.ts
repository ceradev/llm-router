import type { AdminEvaluationMode } from "@/shared/api/admin"

export type AdminTab = "overview" | "models" | "requests" | "sync"

export type DropdownOption = {
  value: string
  label: string
}

export type AvailabilityFilter = "" | "true" | "false"
export type BatchStatusFilter = "" | "cataloged" | "provisional" | "verified" | "rejected" | "deprecated"

export type BatchProgress = {
  total: number
  completed: number
  currentRoutingKey: string | null
}

export type OverviewCard = {
  label: string
  value: string | number
}

export type BatchMode = AdminEvaluationMode
