import type { AuditResponse } from '../types/api'
import type { ResultView } from './ResultNavigation'
import { ScoreCard } from './ScoreCard'
import { StatusBadge } from './StatusBadge'
import { attentionAreaFromFlag } from '../lib/score'
import { compactSource, formatVerdict, shortSourceMode } from '../lib/presentation'

interface ResultOverviewProps {
  data: AuditResponse
  onNavigate: (view: ResultView) => void
}

function SummaryLink({
  label,
  view,
  onNavigate,
}: {
  label: string
  view: ResultView
  onNavigate: (view: ResultView) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onNavigate(view)}
      className="inline-flex min-h-10 items-center justify-center rounded-lg border border-border px-3 text-xs font-medium text-muted transition-colors hover:border-brand/30 hover:text-brand"
    >
      {label}
    </button>
  )
}

export function ResultOverview({ data, onNavigate }: ResultOverviewProps) {
  const scoring = data.audit.scoring
  const diagnosis = data.audit.diagnosis
  const executive = data.audit.executive_report
  const identity = data.audit.project_understanding?.project_identity
  const hardFlags = diagnosis?.hard_flags || []
  const evidenceConfidence = diagnosis?.evidence_confidence
  const evidenceLabel = evidenceConfidence?.label || 'unknown'
  const recommendations = data.audit.recommendations_v2 || []
  const supportingActions = recommendations.slice(1, 3)
  const nextMove = executive?.recommended_next_move
  const unassessed = scoring?.unassessed_categories || diagnosis?.repository_health?.unassessed_categories || []
  const claim =
    diagnosis?.repository_health?.claim ||
    executive?.readiness_claim ||
    executive?.headline ||
    formatVerdict(diagnosis?.repository_health?.label)
  const reason = diagnosis?.repository_health?.summary || executive?.one_sentence_summary

  return (
    <section className="space-y-3" aria-label="Audit summary">
      <div className="surface-raised overflow-hidden rounded-xl">
        <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[minmax(0,1fr)_250px]">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-1.5">
              <span className="rounded-full border border-border bg-base px-2.5 py-1 text-[11px] font-medium text-faint">
                {shortSourceMode(data.source_type)}
              </span>
              <span className="rounded-full border border-border bg-base px-2.5 py-1 text-[11px] font-medium text-faint">
                {(data.audit.analysis?.mode || data.analysis_mode).replace(/_/g, ' ')}
              </span>
              {diagnosis?.repository_health && (
                <StatusBadge
                  label={diagnosis.repository_health.label}
                  score={diagnosis.repository_health.score ?? undefined}
                />
              )}
              <span className="rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 text-[11px] font-medium text-warning">
                Evidence: {evidenceLabel}
              </span>
            </div>

            <h2 className="text-xl font-semibold leading-tight tracking-tight text-primary sm:text-[22px]">{claim}</h2>
            <p className="mt-1 break-anywhere font-mono text-[12.5px] leading-5 text-faint">
              {compactSource(data.source_value)}
            </p>
            {reason && (
              <p className="mt-2.5 max-w-2xl text-sm leading-5 text-muted">
                {reason}
              </p>
            )}

            {hardFlags.length > 0 ? (
              <div className="mt-3 rounded-lg border border-error/30 bg-error/5 p-2.5">
                <div className="text-xs font-medium text-error">Confirmed blockers</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {hardFlags.map((flag) => (
                    <span
                      key={flag}
                      className="rounded-full border border-error/30 bg-error/10 px-2.5 py-1 text-[11px] font-medium text-error"
                    >
                      {attentionAreaFromFlag(flag)}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mt-3 rounded-lg border border-health/25 bg-health/5 p-2.5 text-sm font-medium text-health">
                No release-blocking issues were confirmed by the checks DrRepo could run.
              </div>
            )}

            <div className="mt-3 rounded-xl border border-border bg-base/70 p-3">
              <h3 className="text-sm font-semibold text-primary">Recommended next move</h3>
              {nextMove ? (
                <div className="mt-2 border-l-2 border-brand pl-3">
                  <div className="text-sm font-semibold text-primary">{nextMove.title}</div>
                  {nextMove.reason && <p className="mt-1.5 text-sm leading-5 text-muted">{nextMove.reason}</p>}
                  {nextMove.first_step && <p className="mt-2 text-sm leading-5 text-primary">{nextMove.first_step}</p>}
                  {nextMove.success_check && (
                    <p className="mt-1.5 text-sm leading-5 text-muted">
                      <span className="font-medium text-primary">Success check:</span> {nextMove.success_check}
                    </p>
                  )}
                </div>
              ) : (
                <p className="mt-2 text-sm leading-5 text-muted">Open the fix plan and review evidence limitations.</p>
              )}
              {supportingActions.length > 0 && (
                <div className="mt-3 border-t border-border pt-2.5">
                  <div className="text-xs font-medium uppercase tracking-[0.12em] text-faint">
                    Additional actions
                  </div>
                  <ol className="mt-1.5 space-y-1.5">
                    {supportingActions.map((action) => (
                      <li key={action.id || action.title} className="text-sm leading-5 text-muted">
                        <span className="font-medium text-primary">{action.title}</span>
                        {action.why_it_matters ? ` - ${action.why_it_matters}` : ''}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              <SummaryLink label="Open fix plan" view="fix_plan" onNavigate={onNavigate} />
              <SummaryLink label="Review issues" view="issues" onNavigate={onNavigate} />
              <SummaryLink label="View technical details" view="technical_details" onNavigate={onNavigate} />
            </div>
          </div>

          <ScoreCard
            title="Observed score"
            score={scoring?.observed_score ?? scoring?.overall_score}
            label={diagnosis?.repository_health?.label}
            subtitle={evidenceLabel !== 'full' ? 'Observed score based on limited evidence.' : 'Based on assessed audit evidence.'}
            size="hero"
            evidenceLabel={evidenceLabel}
            assessedWeightRatio={scoring?.assessed_weight_ratio ?? diagnosis?.repository_health?.assessed_weight_ratio}
            unassessedCount={unassessed.length}
          />
        </div>
      </div>

      <div className="grid gap-4">
        <div className="rounded-xl border border-border bg-surface p-3.5 sm:p-4">
          <h3 className="text-sm font-semibold text-primary">Project identity</h3>
          <p className="mt-2 text-sm leading-5 text-muted">
            {identity?.project_type || 'Project type not identified'}
            {identity?.primary_language ? ` - ${identity.primary_language}` : ''}
            {identity?.architecture_type ? ` - ${identity.architecture_type}` : ''}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {[...(identity?.frameworks || []), ...(identity?.interfaces || [])].slice(0, 6).map((item) => (
              <span key={item} className="rounded-full border border-border bg-base px-2 py-1 text-[12.5px] text-faint">
                {item}
              </span>
            ))}
          </div>
          <p className="mt-2 text-[13px] text-faint">Identity confidence: {identity?.confidence || 'unknown'}</p>
        </div>
      </div>

      {unassessed.length > 0 && (
        <div className="rounded-xl border border-warning/25 bg-warning/5 p-3.5">
          <h3 className="text-sm font-semibold text-warning">Could not be verified</h3>
          <p className="mt-1.5 text-sm leading-5 text-muted">
            {unassessed.slice(0, 5).join(', ')} were not assessed and were not counted as clean evidence.
          </p>
        </div>
      )}
    </section>
  )
}
