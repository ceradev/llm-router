import { useEffect, useRef, useState } from "react"

import { fieldClass } from "@/features/admin/constants"
import type { DropdownOption } from "@/features/admin/types"

export function CustomDropdown({
  value,
  options,
  onChange,
  placeholder,
  className,
}: Readonly<{
  value: string
  options: DropdownOption[]
  onChange: (next: string) => void
  placeholder: string
  className?: string
}>) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement | null>(null)
  const selected = options.find((option) => option.value === value)

  useEffect(() => {
    function handleOutside(event: MouseEvent) {
      if (!rootRef.current) return
      if (!rootRef.current.contains(event.target as Node)) setOpen(false)
    }
    globalThis.addEventListener("mousedown", handleOutside)
    return () => globalThis.removeEventListener("mousedown", handleOutside)
  }, [])

  return (
    <div ref={rootRef} className={`relative z-40 min-w-44 ${className ?? ""}`}>
      <button
        type="button"
        className={`${fieldClass} flex w-full items-center justify-between text-left`}
        onClick={() => setOpen((current) => !current)}
      >
        <span>{selected?.label ?? placeholder}</span>
        <span className="text-xs text-(--text-muted)">▼</span>
      </button>
      {open ? (
        <div className="absolute top-full z-120 mt-2 max-h-56 w-full overflow-auto rounded-xl border border-(--border-subtle) bg-[#0f1425] shadow-(--shadow-card)">
          {options.map((option) => (
            <button
              key={option.value || "__empty"}
              type="button"
              className="w-full px-3 py-2 text-left text-sm text-(--text-primary) transition-colors hover:bg-(--surface-glass)"
              onClick={() => {
                onChange(option.value)
                setOpen(false)
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
