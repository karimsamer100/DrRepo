import type { AuditResponse } from '../types/api'
import { ScoreCard } from './ScoreCard'
import { StatusBadge } from './StatusBadge'
import {
  attentionAreaFromFlag,
  getFindingFamilies,
  scoreColor,
} from '../lib/score'

interface ResultOverviewProps {
  data: AuditResponse
}

function CategoryBar({ label, score }: { label: string; score: number }) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="w-28 shrink-0 text-[11px] text-muted capitalize">{label}</div>
      <div className="flex-1 h-1.5 rounded-full bg-surface-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-[width] ${
            score >= 85 ? 'bg-health' : score >= 70 ? 'bg-attention' : score >= 50 ? 'bg-warning' : 'bg-error'
          }`}
          style={{ width: `${score}%` }}
        />
      </div>
      <div className={`w-8 text-right text-xs font-mono font-medium ${scoreColor(score)}`}>{score}</div>
    </div>
  )
}

export function ResultOverview({ data }: ResultOverviewProps) {
  const scoring = data.audit.scoring
  const diagnosis = data.audit.diagnosis
  const hardFlags = diagnosis?.hard_flags || []

  const families = getFindingFamilies(data.audit)
  const issueFamilies = families.filter((f) => f.count > 0)
  const hasIssues = hardFlags.length > 0 || issueFamilies.length > 0
  const isHealthy =
    (scoring?.overall_score ?? 0) >= 85 && !hasIssues

  const categories = scoring?.categories || {}
  const categoryEntries = Object.entries(categories).filter(
    ([, score]) => typeof score === 'number'
  ) as [string, number][]

  const attentionAreas = Array.from(
    new Set([
      ...hardFlags.map(attentionAreaFromFlag),
      ...issueFamilies.map((f) => f.family),
    ])
  )

  return (
    <section className="space-y-5 animate-fade-up">
      {hasIssues && (
        <div className="rounded-md border border-error/30 bg-error/5 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-error mb-1.5">
            Attention areas
          </div>
          <p className="text-sm text-primary">
            {attentionAreas.join(' · ')}
          </p>
        </div>
      )}

      {isHealthy && (
        <div className="rounded-md border border-health/30 bg-health/5 p-3">
          <p className="text-sm text-health">
            Core checks look good — no critical issues detected.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-faint">
            Repository
          </div>
          <div className="font-mono text-sm text-primary break-all">{data.source_value}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="rounded-full border border-health/30 bg-health/10 px-2 py-0.5 text-[11px] font-medium text-health">
            {data.status}
          </span>
          {diagnosis?.repository_health && (
            <StatusBadge
              label={diagnosis.repository_health.label}
              score={diagnosis.repository_health.score ?? undefined}
            />
          )}
        </div>
      </div>

      {diagnosis?.repository_health?.summary && (
        <p className="text-sm text-primary leading-relaxed">
          {diagnosis.repository_health.summary}
        </p>
      )}

      <div className="space-y-3">
        <ScoreCard title="Overall score" score={scoring?.overall_score} size="hero" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <ScoreCard title="Repository Health" score={scoring?.repository_health_score} />
          <ScoreCard title="Portfolio Readiness" score={scoring?.portfolio_readiness_score} />
        </div>
      </div>

      {categoryEntries.length > 0 && (
        <div className="rounded-lg border border-border bg-surface p-4">
          <h3 className="text-xs font-medium text-muted mb-2">Category scores</h3>
          <div className="max-w-md divide-y divide-border/50">
            {categoryEntries.map(([key, score]) => (
              <CategoryBar key={key} label={key.replace(/_/g, ' ')} score={score} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
