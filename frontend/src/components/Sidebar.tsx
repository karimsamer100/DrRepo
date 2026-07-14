import { useState } from 'react'

interface SidebarProps {
  onReset: () => void
}

function Logo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
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

function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <span className="flex min-w-0 items-center gap-2.5">
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-brand/25 bg-brand/10 text-brand">
        <Logo className="h-5 w-5" />
      </span>
      {!collapsed && (
        <span className="min-w-0">
          <span className="block text-base font-semibold tracking-tight text-white">DrRepo</span>
          <span className="block text-[10px] font-medium uppercase tracking-[0.18em] text-faint">
            Diagnostic console
          </span>
        </span>
      )}
    </span>
  )
}

export function Sidebar({ onReset }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`shrink-0 border-border bg-panel transition-[width] duration-200 ease-out-strong sm:flex sm:min-h-dvh sm:flex-col sm:border-r ${
        collapsed ? 'sm:w-[4.5rem]' : 'sm:w-64'
      }`}
    >
      <div className="flex items-center justify-between border-b border-border px-3 py-2.5 sm:px-3 sm:py-3">
        <button
          type="button"
          onClick={onReset}
          className="flex min-h-11 min-w-0 items-center rounded-xl px-1 text-left transition-colors hover:bg-white/[0.03]"
          aria-label="Start a new diagnostic"
          title="New diagnostic"
        >
          <Brand collapsed={collapsed} />
        </button>

        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="hidden min-h-10 min-w-10 place-items-center rounded-xl text-muted transition-colors hover:bg-white/[0.03] hover:text-primary sm:grid"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            {collapsed ? <path d="m9 18 6-6-6-6" /> : <path d="m15 18-6-6 6-6" />}
          </svg>
        </button>
      </div>

      <nav className={`hidden py-3 sm:block ${collapsed ? 'px-2' : 'px-3'}`} aria-label="Primary">
        {!collapsed && (
          <div className="mb-2 px-3 text-[11px] font-medium uppercase tracking-[0.18em] text-faint">
            Workspace
          </div>
        )}
        <button
          type="button"
          onClick={onReset}
          className="flex min-h-11 w-full items-center gap-3 rounded-xl border border-brand/20 bg-brand/10 px-3 py-2 text-left text-brand transition-colors hover:bg-brand/15"
          aria-label="Open audit workspace"
          title="Audit workspace"
        >
          <svg
            className="h-4 w-4 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
            <path d="M8 13h8M8 17h5" />
          </svg>
          {!collapsed && <span className="text-sm font-medium">Audit workspace</span>}
        </button>
      </nav>

      <div className="mt-auto hidden border-t border-border px-5 py-4 sm:block">
        {!collapsed && (
          <div>
            <p className="text-[10px] leading-relaxed text-faint">
              Evidence-driven repository health, readiness, and remediation.
            </p>
            <p className="mt-2 text-[10px] text-faint/70">v0.1 - local workspace</p>
          </div>
        )}
      </div>
    </aside>
  )
}
