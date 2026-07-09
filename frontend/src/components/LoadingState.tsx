const stages = [
  'Resolve path',
  'Scan repository',
  'Collect evidence',
  'Score health',
  'Build advisor plan',
]

export function LoadingState() {
  return (
    <div className="w-full max-w-3xl mx-auto animate-fade-up">
      <div className="h-0.5 w-full bg-border overflow-hidden rounded-full mb-8">
        <div className="h-full w-1/3 bg-brand animate-[shimmer_1.5s_ease-in-out_infinite]" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="rounded-lg border border-border bg-surface p-4 h-28 animate-shimmer"
          />
        ))}
      </div>

      <div className="rounded-lg border border-border bg-surface p-6 animate-shimmer">
        <div className="h-4 w-1/3 rounded bg-surface-2 mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-3 w-full rounded bg-surface-2" />
          ))}
        </div>
      </div>

      <div className="mt-6 flex items-center justify-center gap-6 text-[11px] text-muted uppercase tracking-wider">
        {stages.map((stage, i) => (
          <span key={stage} className="flex items-center gap-2">
            <span className="h-4 w-4 rounded-full border border-border bg-surface-2 flex items-center justify-center text-[9px]">
              {i + 1}
            </span>
            {stage}
          </span>
        ))}
      </div>
    </div>
  )
}
