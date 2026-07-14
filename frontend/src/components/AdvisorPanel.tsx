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
  const actionText = unique(group.items.map((item) => item.action)).find(
    (action) => normalizeTitle(action) !== group.key
  )

  return (
    <>
      {actionText && <p className="mt-2 text-sm leading-6 text-muted">{actionText}</p>}
      <EvidenceChips items={group.items} />
      <WhyItMatters items={group.items} />
    </>
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

      {optional.length > 0 && (
        <div className="mb-4 rounded-xl border border-border bg-base p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-faint">
            Optional audit-environment improvements
          </div>
          <ul className="mt-2 space-y-1">
            {optional.map((item) => (
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
