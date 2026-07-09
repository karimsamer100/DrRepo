import { useEffect, useState } from 'react'
import { getHealth } from '../api/client'

export function AuditConsoleHeader({ onNew }: { onNew?: () => void }) {
  const [health, setHealth] = useState<'ok' | 'error' | 'checking'>('checking')

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then(() => {
        if (!cancelled) setHealth('ok')
      })
      .catch(() => {
        if (!cancelled) setHealth('error')
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <header className="h-14 border-b border-border bg-surface flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-primary tracking-wide">
          Audit Console
        </h1>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
            health === 'ok'
              ? 'border-health/30 bg-health/10 text-health'
              : health === 'error'
              ? 'border-error/30 bg-error/10 text-error'
              : 'border-border bg-surface-2 text-faint'
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              health === 'ok'
                ? 'bg-health'
                : health === 'error'
                ? 'bg-error'
                : 'bg-faint animate-pulse'
            }`}
          />
          {health === 'ok' ? 'API online' : health === 'error' ? 'API offline' : 'Checking'}
        </span>
      </div>
      {onNew && (
        <button
          type="button"
          onClick={onNew}
          className="rounded-md border border-brand/40 bg-brand/10 px-3 py-1.5 text-xs font-medium text-brand hover:bg-brand/20 transition-all active:scale-[0.98]"
        >
          New diagnostic
        </button>
      )}
    </header>
  )
}
