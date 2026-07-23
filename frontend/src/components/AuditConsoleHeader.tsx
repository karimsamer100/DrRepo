import { useEffect, useState } from 'react'
import { getHealth } from '../api/client'

function HeaderMark() {
  return (
    <svg
      className="h-5 w-5"
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="1" y="1" width="26" height="26" rx="7" stroke="currentColor" strokeWidth="2" />
      <path d="M7 14h14M14 7v14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M19.5 8.5h3M19.5 14h2.2M19.5 19.5h3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

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
    <header className="flex min-h-16 items-center justify-between border-b border-border bg-panel px-4 lg:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-brand/25 bg-brand/10 text-brand">
          <HeaderMark />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold tracking-tight text-primary">DrRepo</div>
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-faint">
            Repository Audit
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span
          role="status"
          aria-live="polite"
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
      {onNew && (
        <button
          type="button"
          onClick={onNew}
          className="inline-flex min-h-10 items-center rounded-xl border border-border px-3 text-xs font-medium text-faint transition-colors duration-150 ease-out-strong hover:border-brand/30 hover:bg-brand/5 hover:text-brand"
        >
          New diagnostic
        </button>
      )}
      </div>
    </header>
  )
}
