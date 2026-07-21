import { useRef, type KeyboardEvent } from 'react'

export type ResultView = 'overview' | 'actions' | 'findings' | 'devops' | 'architecture' | 'evidence'

interface ResultNavigationProps {
  activeView: ResultView
  onViewChange: (view: ResultView) => void
  counts?: Partial<Record<ResultView, number>>
}

const RESULT_VIEWS: Array<{ id: ResultView; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'actions', label: 'Actions' },
  { id: 'findings', label: 'Findings' },
  { id: 'devops', label: 'DevOps' },
  { id: 'architecture', label: 'Architecture' },
  { id: 'evidence', label: 'Evidence' },
]

export function ResultNavigation({ activeView, onViewChange, counts = {} }: ResultNavigationProps) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex: number | null = null
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % RESULT_VIEWS.length
    if (event.key === 'ArrowLeft') nextIndex = (index - 1 + RESULT_VIEWS.length) % RESULT_VIEWS.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = RESULT_VIEWS.length - 1
    if (nextIndex === null) return

    event.preventDefault()
    const nextView = RESULT_VIEWS[nextIndex]
    onViewChange(nextView.id)
    tabRefs.current[nextIndex]?.focus()
  }

  return (
    <nav
      className="sticky top-0 z-20 mb-6 border-y border-border bg-base py-2"
      aria-label="Audit result sections"
    >
      <div className="overflow-x-auto pb-1" role="tablist" aria-label="Audit result sections">
        <div className="flex min-w-max gap-1">
          {RESULT_VIEWS.map((view, index) => {
            const active = activeView === view.id
            const count = counts[view.id]
            return (
              <button
                key={view.id}
                ref={(element) => {
                  tabRefs.current[index] = element
                }}
                id={`result-tab-${view.id}`}
                type="button"
                role="tab"
                aria-selected={active}
                aria-controls={`result-panel-${view.id}`}
                aria-current={active ? 'page' : undefined}
                tabIndex={active ? 0 : -1}
                onClick={() => onViewChange(view.id)}
                onKeyDown={(event) => handleKeyDown(event, index)}
                className={`inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-brand/10 text-brand shadow-[0_0_0_1px_rgba(34,211,238,0.16)_inset]'
                    : 'text-muted hover:bg-white/[0.03] hover:text-primary'
                }`}
              >
                {view.label}
                {typeof count === 'number' && count > 0 && (
                  <span className="rounded-full border border-current/20 px-1.5 py-0.5 font-mono text-[10px]">
                    {count}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
