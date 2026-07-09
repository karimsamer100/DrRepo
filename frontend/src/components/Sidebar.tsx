interface SidebarProps {
  onReset: () => void
}

export function Sidebar({ onReset }: SidebarProps) {
  return (
    <aside className="w-56 shrink-0 border-r border-border bg-surface flex flex-col">
      <button
        type="button"
        onClick={onReset}
        className="flex items-center gap-3 px-5 py-4 border-b border-border hover:bg-surface-2 transition-colors text-left w-full"
      >
        <div className="h-6 w-6 rounded bg-brand flex items-center justify-center shrink-0">
          <span className="text-xs font-bold text-base">D</span>
        </div>
        <span className="font-semibold text-base text-primary">DrRepo</span>
      </button>
      <nav className="px-3 py-4">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-faint px-3 mb-2">
          Console
        </div>
        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-3 px-3 py-2 rounded-md bg-brand/10 text-brand border border-brand/20 hover:bg-brand/20 transition-colors w-full text-left"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <span className="text-sm font-medium">Audit</span>
        </button>
      </nav>
      <div className="mt-auto px-5 py-4 border-t border-border">
        <p className="text-[10px] text-faint leading-relaxed">
          Evidence-driven repository health, readiness, and remediation.
        </p>
      </div>
    </aside>
  )
}
