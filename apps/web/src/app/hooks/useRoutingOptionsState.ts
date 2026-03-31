import { useCallback, useState } from "react"

import type {
  Priority,
  ResponseDepth,
  UseCaseId,
} from "@/features/landing/types/routingOptions"

type RoutingOptionsState = {
  priority: Priority
  setPriority: (value: Priority) => void
  useCases: Set<UseCaseId>
  toggleUseCase: (id: UseCaseId) => void
  providers: Set<string>
  toggleProvider: (provider: string) => void
  responseDepth: ResponseDepth
  setResponseDepth: (value: ResponseDepth) => void
}

export function useRoutingOptionsState(): RoutingOptionsState {
  const [priority, setPriority] = useState<Priority>("quality")
  const [useCases, setUseCases] = useState<Set<UseCaseId>>(
    () => new Set(["api"]),
  )
  const [providers, setProviders] = useState<Set<string>>(
    () => new Set(),
  )
  const [responseDepth, setResponseDepth] = useState<ResponseDepth>("balanced")

  const toggleUseCase = useCallback((id: UseCaseId) => {
    setUseCases((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  const toggleProvider = useCallback((provider: string) => {
    setProviders((prev) => {
      const next = new Set(prev)
      next.has(provider) ? next.delete(provider) : next.add(provider)
      return next
    })
  }, [])

  return {
    priority,
    setPriority,
    useCases,
    toggleUseCase,
    providers,
    toggleProvider,
    responseDepth,
    setResponseDepth,
  }
}
