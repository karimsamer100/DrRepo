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

function dedupeWhyItMatters(items: AdvisorAction[]): string[] {
  const seen = new Set<string>()
  const result: string[] = []

  items.forEach((item) => {
    if (!item.why_it_matters) return
    const normalized = item.why_it_matters.trim()
    if (normalized.length === 0) return
    if (seen.has(normalized)) return
    seen.add(normalized)
    result.push(item.why_it_matters)
  })

  return result
}

function WhyItMatters({ items }: { items: AdvisorAction[] }) {
  const uniqueWhys = dedupeWhyItMatters(items)
  if (uniqueWhys.length === 0) return null

  return (
    <details className="mt-1">
      <summary className="text-[11px] text-muted cursor-pointer hover:text-primary transition-colors">
        Why it matters
      </summary>
      <ul className="mt-1.5 space-y-1 pl-1">
        {uniqueWhys.map((why, i) => (
          <li key={i} className="text-xs text-muted">
            {why}
          </li>
        ))}
      </ul>
    </details>
  )
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
    <section className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-xs font-medium text-muted">Advisor</h3>
        <span className="rounded-full border border-brand/30 bg-brand/10 px-2 py-0.5 text-[10px] font-medium text-brand">
          {profileName}
        </span>
      </div>

      {summary && (
        <div className="rounded-lg border border-border bg-surface-2 p-3 mb-4">
          <p className="text-sm text-primary leading-relaxed">{summary}</p>
        </div>
      )}

      {fixNow.length > 0 && (
        <div className="mb-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="h-2 w-2 rounded-full bg-error" />
            <div className="text-[11px] font-medium uppercase tracking-wider text-error">
              Fix now
            </div>
          </div>

          {fixNow[0] && (
            <div className="rounded-lg border border-error/30 bg-error/5 p-4 mb-3">
              <div className="text-[11px] font-medium uppercase tracking-wider text-error mb-1.5">
                Start here
              </div>
              <div className="text-base font-semibold text-primary mb-1">{fixNow[0].title}</div>
              <WhyItMatters items={fixNow[0].items} />
            </div>
          )}

          {fixNow.length > 1 && (
            <ol className="space-y-2">
              {fixNow.slice(1).map((group, index) => (
                <li key={group.key} className="flex items-start gap-3 rounded-md border border-border bg-surface-2 px-3 py-2">
                  <span className="mt-0.5 text-[10px] font-mono text-error/80 w-4 text-right">
                    {index + 2}
                  </span>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-primary">{group.title}</div>
                    <WhyItMatters items={group.items} />
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {fixNext.length > 0 && (
        <div className="mb-5">
          <div className="text-[11px] font-medium uppercase tracking-wider text-attention mb-2">
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
                      <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] font-mono text-faint">
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
          <div className="text-[11px] font-medium uppercase tracking-wider text-faint mb-1.5">
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
