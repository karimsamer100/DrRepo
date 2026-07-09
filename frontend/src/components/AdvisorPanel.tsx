import type { AdvisorAction, AdvisorReport } from '../types/api'

interface AdvisorPanelProps {
  advisor: AdvisorReport | null
  profileId: string
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
    const title = action.title || 'Priority'
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

export function AdvisorPanel({ advisor, profileId }: AdvisorPanelProps) {
  if (!advisor) return null

  const response = advisor.advisor_response
  const plan = advisor.profiled_action_plan
  const profileName = plan?.profile?.display_name || profileId
  const summary = response?.summary || plan?.profile_fit_summary || advisor.summary_lines?.[0]
  const fixNow = dedupeActions(response?.top_priorities || plan?.top_priorities)
  const fixNext = dedupeActions(response?.lower_priority_items || plan?.lower_priority_items)
  const limitations = response?.limitations || []
  const optional = response?.next_steps || []

  if (!summary && fixNow.length === 0 && fixNext.length === 0) return null

  return (
    <section className="animate-fade-up [animation-delay:240ms] rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center justify-between mb-1">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-faint">
            Remediation plan
          </div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-faint">
            Advisor
          </h3>
        </div>
        <span className="rounded-full border border-brand/30 bg-brand/10 px-2 py-0.5 text-[10px] font-medium text-brand">
          {profileName}
        </span>
      </div>

      {summary && <p className="text-sm text-primary mb-4">{summary}</p>}

      {fixNow.length > 0 && (
        <div className="mb-5">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-error mb-2">
            Fix now
          </div>
          <ol className="space-y-3">
            {fixNow.map((group, index) => (
              <li key={group.key} className="flex items-start gap-3">
                <span className="mt-0.5 text-[10px] font-mono text-error/80 w-4 text-right">
                  {index + 1}
                </span>
                <div className="flex-1 border-l-2 border-error/60 pl-3">
                  <div className="text-sm font-medium text-primary">{group.title}</div>
                  {group.items.some((item) => item.why_it_matters) && (
                    <details className="mt-1">
                      <summary className="text-[11px] text-muted cursor-pointer hover:text-primary transition-colors">
                        Why it matters
                      </summary>
                      <ul className="mt-1.5 space-y-1 pl-1">
                        {group.items.map(
                          (item, i) =>
                            item.why_it_matters && (
                              <li key={i} className="text-xs text-muted">
                                {item.why_it_matters}
                              </li>
                            )
                        )}
                      </ul>
                    </details>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {fixNext.length > 0 && (
        <div className="mb-5">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-attention mb-2">
            Fix next
          </div>
          <div className="divide-y divide-border/50">
            {fixNext.map((group) => (
              <div
                key={group.key}
                className="flex items-start gap-3 py-2 first:pt-0 last:pb-0"
              >
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-attention/60" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-primary">{group.title}</span>
                    {group.items.length > 1 && (
                      <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] text-faint">
                        {group.items.length}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {optional.length > 0 && (
        <div className="mb-4">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-faint mb-1.5">
            Optional improvements
          </div>
          <ul className="space-y-1">
            {optional.map((item, i) => (
              <li key={i} className="text-xs text-muted">{item}</li>
            ))}
          </ul>
        </div>
      )}

      {limitations.length > 0 && (
        <details className="pt-3 border-t border-border">
          <summary className="text-[11px] text-muted cursor-pointer hover:text-primary transition-colors">
            Evidence limitations
          </summary>
          <ul className="mt-2 space-y-1 pl-1">
            {limitations.map((item, i) => (
              <li key={i} className="text-xs text-muted">{item}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
