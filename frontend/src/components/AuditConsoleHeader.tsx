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
    <header className="h-12 border-b border-border bg-panel flex items-center justify-between px-4 lg:px-6">
      <div className="flex items-center gap-3">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
            health === 'ok'
              ? 'border-brand/30 bg-brand/10 text-brand'
              : health === 'error'
              ? 'border-error/30 bg-error/10 text-error'
              : 'border-border bg-surface-2 text-faint'
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              health === 'ok'
                ? 'bg-brand'
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
          className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-faint hover:border-brand/30 hover:text-brand hover:bg-brand/5 transition-colors duration-150 ease-out-strong"
        >
          New diagnostic
        </button>
      )}
    </header>
  )
}
