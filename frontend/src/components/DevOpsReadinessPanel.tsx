import type { DevOpsReadiness } from '../types/api'

interface DevOpsReadinessPanelProps {
  readiness?: DevOpsReadiness
}

function scoreText(score?: number | null) {
  return typeof score === 'number' ? `${score}` : 'Not assessed'
}

function statusTone(status?: string) {
  if (status === 'ready') return 'border-health/25 bg-health/5 text-health'
  if (status === 'blocked') return 'border-error/30 bg-error/5 text-error'
  if (status === 'needs_work') return 'border-warning/30 bg-warning/5 text-warning'
  return 'border-border bg-base text-muted'
}

export function DevOpsReadinessPanel({ readiness }: DevOpsReadinessPanelProps) {
  if (!readiness || readiness.applicability === 'not_applicable') return null

  const dimensions = readiness.dimensions || []
  const blockers = readiness.blockers || []
  const strengths = readiness.strengths || []

  return (
    <section className="rounded-2xl border border-border bg-surface p-4">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
            DevOps & release readiness
          </h3>
          <p className="mt-2 text-sm leading-6 text-primary">
            {readiness.verdict?.replace(/_/g, ' ') || 'unknown'} · {scoreText(readiness.observed_score)} observed · confidence {readiness.evidence_confidence || 'unknown'}
          </p>
        </div>
        <span className="self-start rounded-full border border-border bg-base px-2.5 py-1 font-mono text-[12.5px] text-faint">
          Static only
        </span>
      </div>

      {readiness.next_best_step && (
        <div className="mb-4 rounded-xl border border-brand/25 bg-brand/5 p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-brand">
            Release next step
          </div>
          <p className="mt-1 text-sm leading-6 text-primary">{readiness.next_best_step}</p>
        </div>
      )}

      {blockers.length > 0 && (
        <div className="mb-4 rounded-xl border border-error/30 bg-error/5 p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-error">
            Release blockers
          </div>
          <ul className="mt-2 space-y-1">
            {blockers.slice(0, 4).map((blocker) => (
              <li key={blocker.id || blocker.title} className="text-xs leading-5 text-muted">
                <span className="text-primary">{blocker.title}</span>
                {blocker.suggested_fix && ` - ${blocker.suggested_fix}`}
              </li>
            ))}
          </ul>
        </div>
      )}
      {blockers.length === 0 && (
        <div className="mb-4 rounded-xl border border-health/25 bg-health/5 p-3 text-sm leading-6 text-muted">
          <span className="font-medium text-health">No release blockers were confirmed</span> by the checks DrRepo could run.
        </div>
      )}

      {strengths.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {strengths.slice(0, 5).map((strength) => (
            <span key={strength} className="rounded-full border border-health/25 bg-health/5 px-2 py-1 text-[12.5px] text-health">
              {strength}
            </span>
          ))}
        </div>
      )}

      <div className="space-y-2">
        {dimensions.map((dimension) => (
          <details key={dimension.id || dimension.title} className={`rounded-xl border px-3 py-2 ${statusTone(dimension.status)}`}>
            <summary className="flex min-h-8 cursor-pointer list-none items-center justify-between gap-3 text-xs [&::-webkit-details-marker]:hidden">
              <span className="font-medium text-primary">{dimension.title || dimension.id}</span>
              <span className="shrink-0 font-mono text-[12px] uppercase tracking-[0.1em]">
                {dimension.applicability === 'not_applicable' ? 'not applicable' : `${dimension.status || 'unknown'} · ${scoreText(dimension.score)}`}
              </span>
            </summary>
            <p className="mt-2 text-xs leading-5 text-muted">{dimension.summary}</p>
            {dimension.unverified_checks && dimension.unverified_checks.length > 0 && (
              <p className="mt-2 text-xs leading-5 text-faint">
                Unverified: {dimension.unverified_checks.slice(0, 5).join(', ')}
              </p>
            )}
          </details>
        ))}
      </div>
    </section>
  )
}
