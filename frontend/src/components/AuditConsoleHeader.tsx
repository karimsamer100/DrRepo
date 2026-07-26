import { useEffect, useState } from 'react'
import { getHealth } from '../api/client'
import type { ResolvedTheme, ThemePreference } from '../App'

interface AuditConsoleHeaderProps {
  onNew: () => void
  themePreference: ThemePreference
  resolvedTheme: ResolvedTheme
  onThemePreferenceChange: (preference: ThemePreference) => void
}

function HeaderMark() {
  return (
    <svg
      className="h-6 w-6"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="5" y="6" width="20" height="18" rx="3.5" stroke="currentColor" strokeWidth="1.8" />
      <path d="M10 11h5.5M10 16h3.5M10 21h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M18 17.5l2.4 2.4 5.1-6.1" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M7.5 4.5h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.55" />
    </svg>
  )
}

export function AuditConsoleHeader({
  onNew,
  themePreference,
  resolvedTheme,
  onThemePreferenceChange,
}: AuditConsoleHeaderProps) {
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

  const toggleTheme = () => {
    const next: ThemePreference = resolvedTheme === 'dark' ? 'light' : 'dark'
    onThemePreferenceChange(next)
  }

  return (
    <header className="flex min-h-14 items-center justify-between border-b border-border bg-panel px-4 lg:px-6">
      <button
        type="button"
        onClick={onNew}
        aria-label="Return to new audit"
        className="group flex min-w-0 cursor-pointer items-center gap-3 rounded-lg pr-2 text-left transition-colors hover:text-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand"
      >
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-brand/25 bg-brand/10 text-brand transition-colors group-hover:bg-brand/15">
          <HeaderMark />
        </span>
        <span className="min-w-0">
          <span className="block text-[15px] font-semibold tracking-tight text-primary transition-colors group-hover:text-brand">DrRepo</span>
          <span className="block text-[11px] font-medium uppercase tracking-[0.12em] text-muted">
            Repository Audit
          </span>
        </span>
      </button>
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} theme`}
          aria-pressed={resolvedTheme === 'dark'}
          className="theme-switch"
          data-theme-state={resolvedTheme}
          title={`Theme preference: ${themePreference}`}
        >
          <span className="theme-switch-symbol theme-switch-sun" aria-hidden="true">
            <svg viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="2.3" stroke="currentColor" strokeWidth="1.5" />
              <path d="M8 1.5v1.4M8 13.1v1.4M14.5 8h-1.4M2.9 8H1.5M12.6 3.4l-1 1M4.4 11.6l-1 1M12.6 12.6l-1-1M4.4 4.4l-1-1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
            </svg>
          </span>
          <span className="theme-switch-symbol theme-switch-moon" aria-hidden="true">
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M12.3 10.1A5.2 5.2 0 0 1 5.9 3.7a5.3 5.3 0 1 0 6.4 6.4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
          </span>
          <span className="theme-switch-knob" aria-hidden="true" />
          <span className="sr-only">Current theme preference: {themePreference}</span>
        </button>
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
        <button
          type="button"
          onClick={onNew}
          className="inline-flex min-h-9 items-center rounded-lg border border-border px-3 text-xs font-medium text-muted transition-colors duration-150 ease-out-strong hover:border-brand/30 hover:bg-brand/5 hover:text-brand"
        >
          New audit
        </button>
      </div>
    </header>
  )
}
