import type { AdvisorAction, AdvisorReport, AIAdvisorResult, StructuredRecommendation } from '../types/api'

interface AdvisorPanelProps {
  advisor: AdvisorReport | null
  aiAdvisor: AIAdvisorResult | null
  profileId: string
  recommendations?: StructuredRecommendation[]
}

function normalizeTitle(title: string): string {
  return title.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim()
}

interface ActionGroup {
  key: string
  title: string
  items: AdvisorAction[]
}

function dedupeActions(actions: AdvisorAction[] = []): ActionGroup[] {
  const groups = new Map<string, ActionGroup>()

  actions.forEach((action) => {
    const title = action.title || action.action || 'Priority'
    const key = normalizeTitle(title)
    const existing = groups.get(key)
    if (existing) {
      existing.items.push(action)
    } else {
      groups.set(key, { key, title, items: [action] })
    }
  })

  return Array.from(groups.values())
}

function unique(values: Array<string | undefined>): string[] {
  const seen = new Set<string>()
  return values
    .map((value) => value?.trim())
    .filter((value): value is string => {
      if (!value || seen.has(value)) return false
      seen.add(value)
      return true
    })
}

function EvidenceChips({ items }: { items: AdvisorAction[] }) {
  const evidence = unique(
    items.flatMap((item) =>
      Array.isArray(item.evidence) ? item.evidence : [item.evidence]
    )
  )
  if (evidence.length === 0) return null

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {evidence.slice(0, 4).map((item) => (
        <span key={item} className="rounded-full border border-border bg-base px-2 py-1 text-[10px] font-mono text-faint">
          {item}
        </span>
      ))}
    </div>
  )
}

function WhyItMatters({ items }: { items: AdvisorAction[] }) {
  const uniqueWhys = unique(items.map((item) => item.why_it_matters))
  if (uniqueWhys.length === 0) return null

  return (
    <details className="mt-3">
      <summary className="inline-flex min-h-8 cursor-pointer items-center text-xs text-muted transition-colors hover:text-primary">
        Why it matters
      </summary>
      <ul className="mt-2 space-y-1">
        {uniqueWhys.map((why) => (
          <li key={why} className="text-xs leading-5 text-muted">
            {why}
          </li>
        ))}
      </ul>
    </details>
  )
}

function ActionBody({ group }: { group: ActionGroup }) {
  const actionText = unique(
    group.items.map((item) => item.action || item.suggested_fix)
  ).find((action) => action && normalizeTitle(action) !== group.key)

  return (
    <>
      {actionText && <p className="mt-2 text-sm leading-6 text-muted">{actionText}</p>}
      <EvidenceChips items={group.items} />
      <WhyItMatters items={group.items} />
    </>
  )
}

function StructuredRecommendationCard({ rec }: { rec: StructuredRecommendation }) {
  const evidenceItems = rec.evidence_items || []
  const affectedFiles = rec.affected_files || []
  return (
    <li className="rounded-2xl border border-border bg-base p-4">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-brand/30 bg-brand/10 font-mono text-xs text-brand">
          {rec.priority || '-'}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <div className="font-semibold text-primary">{rec.title}</div>
            <span className="rounded-full border border-border bg-surface px-2 py-0.5 text-[10px] text-faint">
              {rec.recommendation_type?.replace(/_/g, ' ') || 'recommendation'}
            </span>
            {rec.profile_relevance && (
              <span className="rounded-full border border-brand/25 bg-brand/5 px-2 py-0.5 text-[10px] text-brand">
                {rec.profile_relevance} relevance
              </span>
            )}
          </div>
          {rec.why_it_matters && <p className="mt-2 text-sm leading-6 text-muted">{rec.why_it_matters}</p>}
          {rec.recommended_steps && rec.recommended_steps.length > 0 && (
            <ol className="mt-3 list-decimal space-y-1 pl-4 text-xs leading-5 text-muted">
              {rec.recommended_steps.slice(0, 4).map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          )}
          {(affectedFiles.length > 0 || evidenceItems.length > 0) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {affectedFiles.slice(0, 3).map((path) => (
                <span key={path} className="rounded-full border border-border bg-surface px-2 py-1 font-mono text-[10px] text-faint">
                  {path}
                </span>
              ))}
              {evidenceItems.slice(0, 3).map((item) => (
                <span key={`${item.finding_id || item.code}-${item.path || item.analyzer}`} className="rounded-full border border-border bg-surface px-2 py-1 font-mono text-[10px] text-faint">
                  {[item.code || item.analyzer, item.path, item.line].filter(Boolean).join(':')}
                </span>
              ))}
            </div>
          )}
          {rec.success_check && (
            <div className="mt-3 rounded-lg border border-border bg-surface p-2 text-xs leading-5 text-muted">
              Success check: {rec.success_check}
            </div>
          )}
        </div>
      </div>
    </li>
  )
}

function RecommendationsSection({
  recommendations,
  profileId,
}: {
  recommendations: StructuredRecommendation[]
  profileId: string
}) {
  const repositoryFixes = recommendations.filter((rec) => rec.recommendation_type !== 'audit_environment')
  const auditEnvironment = recommendations.filter((rec) => rec.recommendation_type === 'audit_environment')
  return (
    <section className="rounded-2xl border border-border bg-surface p-4">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
            Recommended actions
          </h3>
          <p className="mt-1 text-xs text-muted">Structured, deterministic plan for {profileId.replace(/_/g, ' ')}</p>
        </div>
        <span className="self-start rounded-full border border-brand/30 bg-brand/10 px-2.5 py-1 text-[10px] font-medium text-brand sm:self-auto">
          Intelligence v1
        </span>
      </div>
      {repositoryFixes.length > 0 ? (
        <ol className="space-y-3">
          {repositoryFixes.slice(0, 3).map((rec) => (
            <StructuredRecommendationCard key={rec.id || rec.title} rec={rec} />
          ))}
        </ol>
      ) : (
        <div className="rounded-xl border border-health/25 bg-health/5 p-3 text-sm text-muted">
          No repository-fix recommendations were generated from observed evidence.
        </div>
      )}
      {repositoryFixes.length > 3 && (
        <details className="mt-4 border-t border-border pt-3">
          <summary className="inline-flex min-h-8 cursor-pointer items-center text-xs text-muted transition-colors hover:text-primary">
            Show {repositoryFixes.length - 3} additional actions
          </summary>
          <ol className="mt-2 space-y-2">
            {repositoryFixes.slice(3).map((rec) => (
              <StructuredRecommendationCard key={rec.id || rec.title} rec={rec} />
            ))}
          </ol>
        </details>
      )}
      {auditEnvironment.length > 0 && (
        <details className="mt-4 border-t border-border pt-3">
          <summary className="inline-flex min-h-8 cursor-pointer items-center text-xs text-muted transition-colors hover:text-primary">
            Audit-environment improvements
          </summary>
          <ol className="mt-2 space-y-2">
            {auditEnvironment.slice(0, 4).map((rec) => (
              <StructuredRecommendationCard key={rec.id || rec.title} rec={rec} />
            ))}
          </ol>
        </details>
      )}
    </section>
  )
}

function AIAdvisorSection({ aiAdvisor, profileId }: { aiAdvisor: AIAdvisorResult; profileId: string }) {
  const source = aiAdvisor.source
  const status = aiAdvisor.status
  const provider = aiAdvisor.provider
  const model = aiAdvisor.model
  const response = aiAdvisor.advisor_response
  const grounding = aiAdvisor.grounding_result
  const fallbackReason = aiAdvisor.fallback_reason

  const limitations = response?.limitations || []
  const nextSteps = response?.next_steps || []

  const isLlm = source === 'llm' || source === 'ai'
  const sourceLabel = isLlm ? 'AI-generated' : 'Deterministic fallback'
  const sourceColor = isLlm ? 'border-brand/30 bg-brand/10 text-brand' : 'border-attention/30 bg-attention/10 text-attention'

  return (
    <section className="mt-6 rounded-2xl border border-border bg-surface p-4">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
            AI advisor annotation
          </h3>
          <p className="mt-1 text-xs text-muted">Explains the canonical fix plan for {profileId.replace(/_/g, ' ')}</p>
        </div>
        <span className={`self-start rounded-full border px-2.5 py-1 text-[10px] font-medium sm:self-auto ${sourceColor}`}>
          {sourceLabel}
        </span>
      </div>

      <div className="mb-4 flex flex-wrap gap-2 text-xs text-muted">
        <span className="rounded-lg border border-border bg-base px-2 py-1">Status: {status}</span>
        {isLlm && provider && (
          <span className="rounded-lg border border-border bg-base px-2 py-1">Provider: {provider}</span>
        )}
        {isLlm && model && (
          <span className="rounded-lg border border-border bg-base px-2 py-1">Model: {model}</span>
        )}
        {grounding && (
          <span className="rounded-lg border border-border bg-base px-2 py-1">
            Grounding: {grounding.valid ? 'valid' : 'rejected'}
            {typeof grounding.validated_references === 'number' && ` (${grounding.validated_references} refs)`}
          </span>
        )}
      </div>

      {grounding && grounding.violations && grounding.violations.length > 0 && (
        <div className="mb-4 rounded-xl border border-error/25 bg-error/5 p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-error">Grounding violations</div>
          {grounding.violation_codes && grounding.violation_codes.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {grounding.violation_codes.slice(0, 6).map((code) => (
                <span key={code} className="rounded-full border border-error/25 bg-base px-2 py-1 font-mono text-[10px] text-error">
                  {code}
                </span>
              ))}
            </div>
          )}
          <ul className="mt-2 space-y-1">
            {grounding.violations.slice(0, 6).map((v) => (
              <li key={v} className="text-xs leading-5 text-muted">
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}

      {fallbackReason && (
        <div className="mb-4 rounded-xl border border-attention/25 bg-attention/5 p-3 text-xs text-muted">
          <span className="font-medium text-attention">Fallback:</span> {fallbackReason}
        </div>
      )}

      {response?.profile_context && (
        <p className="mb-4 text-xs leading-5 text-muted">{response.profile_context}</p>
      )}

      {response?.summary && (
        <div className="mb-5 rounded-xl border border-border bg-base p-3">
          <p className="text-sm leading-6 text-primary">{response.summary}</p>
        </div>
      )}

      {nextSteps.length > 0 && (
        <div className="mb-4 rounded-xl border border-border bg-base p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-faint">
            Success checks / next steps
          </div>
          <ul className="mt-2 space-y-1">
            {nextSteps.map((item) => (
              <li key={item} className="text-xs leading-5 text-muted">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {limitations.length > 0 && (
        <details className="border-t border-border pt-3">
          <summary className="inline-flex min-h-8 cursor-pointer items-center text-xs text-muted transition-colors hover:text-primary">
            Evidence limitations behind this plan
          </summary>
          <ul className="mt-2 space-y-1">
            {limitations.map((item) => (
              <li key={item} className="text-xs leading-5 text-muted">
                {item}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}

export function AdvisorPanel({ advisor, aiAdvisor, profileId, recommendations = [] }: AdvisorPanelProps) {
  const hasRecommendations = recommendations.length > 0
  const response = advisor?.advisor_response
  const plan = advisor?.profiled_action_plan
  const profileName = plan?.profile?.display_name || profileId
  const summary = response?.summary || plan?.profile_fit_summary || advisor?.summary_lines?.[0]
  const fixNow = dedupeActions(response?.top_priorities || plan?.top_priorities)
  const fixNext = dedupeActions(response?.lower_priority_items || plan?.lower_priority_items)

  const showDeterministic = hasRecommendations || summary || fixNow.length > 0 || fixNext.length > 0

  return (
    <>
      {hasRecommendations && <RecommendationsSection recommendations={recommendations} profileId={profileId} />}
      {!hasRecommendations && showDeterministic && (
        <section className="rounded-2xl border border-border bg-surface p-4">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
                Remediation plan
              </h3>
              <p className="mt-1 text-xs text-muted">Prioritized for {profileName}</p>
            </div>
            <span className="self-start rounded-full border border-brand/30 bg-brand/10 px-2.5 py-1 text-[10px] font-medium text-brand sm:self-auto">
              Advisor
            </span>
          </div>

          {summary && (
            <div className="mb-5 rounded-xl border border-border bg-base p-3">
              <p className="text-sm leading-6 text-primary">{summary}</p>
            </div>
          )}

          {fixNow.length > 0 ? (
            <div className="mb-5">
              <div className="mb-3 text-[11px] font-medium uppercase tracking-[0.16em] text-error">
                Fix first
              </div>
              <ol className="space-y-3">
                {fixNow.map((group, index) => (
                  <li key={group.key} className="rounded-2xl border border-error/25 bg-error/5 p-4">
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-error/30 bg-error/10 font-mono text-xs text-error">
                        {index + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-primary">{group.title}</div>
                        <ActionBody group={group} />
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          ) : (
            <div className="mb-5 rounded-xl border border-health/25 bg-health/5 p-3 text-sm text-muted">
              No immediate remediation priorities were returned.
            </div>
          )}

          {fixNext.length > 0 && (
            <div className="mb-5">
              <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.16em] text-attention">
                Fix next
              </div>
              <div className="divide-y divide-border/50 rounded-xl border border-border bg-base">
                {fixNext.map((group) => (
                  <div key={group.key} className="p-3">
                    <div className="text-sm font-medium text-primary">{group.title}</div>
                    <ActionBody group={group} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {aiAdvisor?.requested && <AIAdvisorSection aiAdvisor={aiAdvisor} profileId={profileId} />}
    </>
  )
}
