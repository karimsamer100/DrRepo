import { useRef, type KeyboardEvent } from 'react'

export type ResultView = 'summary' | 'fix_plan' | 'issues' | 'technical_details'

interface ResultNavigationProps {
  activeView: ResultView
  onViewChange: (view: ResultView) => void
  counts?: Partial<Record<ResultView, number>>
}

const RESULT_VIEWS: Array<{ id: ResultView; label: string }> = [
  { id: 'summary', label: 'Summary' },
  { id: 'fix_plan', label: 'Fix Plan' },
  { id: 'issues', label: 'Issues' },
  { id: 'technical_details', label: 'Technical Details' },
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
      className="sticky top-0 z-20 mb-3 -mx-4 border-y border-border bg-base/95 px-4 py-1.5 sm:mx-0 sm:rounded-xl sm:border sm:bg-surface/95"
      aria-label="Audit result sections"
    >
      <div className="overflow-x-auto" role="tablist" aria-label="Audit result sections">
        <div className="mx-auto flex w-max min-w-full gap-1 rounded-lg bg-base p-1 sm:min-w-0">
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
                className={`inline-flex min-h-8 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition-colors sm:min-h-9 ${
                  active
                    ? 'bg-brand text-on-brand'
                    : 'text-muted hover:bg-surface-2/65 hover:text-primary'
                }`}
              >
                {view.label}
                {typeof count === 'number' && count > 0 && (
                  <span className="rounded-full border border-current/20 px-1.5 py-0.5 font-mono text-[12px]">
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
