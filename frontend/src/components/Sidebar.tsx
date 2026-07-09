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
      <rect x="1" y="1" width="26" height="26" rx="5" stroke="currentColor" strokeWidth="2" />
      <path d="M14 7v14M7 14h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M21 4h3v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function Sidebar({ onReset }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`shrink-0 border-r border-border bg-panel flex flex-col transition-[width] duration-200 ease-out-strong ${
        collapsed ? 'w-16' : 'w-56'
      }`}
    >
      <div className="flex items-center justify-between border-b border-border px-3 py-3">
        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-2.5 hover:bg-white/[0.03] transition-colors text-left rounded-md"
          aria-label="Go to new audit"
          title="New audit"
        >
          <Logo className="h-6 w-6 shrink-0 text-brand" />
          {!collapsed && (
            <span className="font-semibold text-base text-white tracking-tight">
              DrRepo
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="rounded-md p-1.5 text-muted hover:bg-white/[0.03] hover:text-primary transition-colors"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            {collapsed ? (
              <path d="m9 18 6-6-6-6" />
            ) : (
              <path d="m15 18-6-6 6-6" />
            )}
          </svg>
        </button>
      </div>

      <nav className={`py-3 ${collapsed ? 'px-2' : 'px-3'}`}>
        {!collapsed && (
          <div className="text-[11px] font-medium uppercase tracking-wider text-faint px-3 mb-2">
            Console
          </div>
        )}
        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-3 px-3 py-2 rounded-md bg-brand/10 text-brand border border-brand/20 hover:bg-brand/15 transition-colors w-full text-left"
          aria-label="Audit"
          title="Audit"
        >
          <svg
            className="w-4 h-4 shrink-0"
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
          </svg>
          {!collapsed && (
            <span className="text-sm font-medium transition-opacity duration-200">Audit</span>
          )}
        </button>
      </nav>

      <div className="mt-auto px-5 py-4 border-t border-border">
        {!collapsed && (
          <div className="transition-opacity duration-200">
            <p className="text-[10px] text-faint leading-relaxed">
              Evidence-driven repository health, readiness, and remediation.
            </p>
            <p className="mt-2 text-[10px] text-faint/70">v0.1 · local audit</p>
          </div>
        )}
      </div>
    </aside>
  )
}
