import { useState } from 'react'
import type { ToolResult } from '../types/api'
import { familyColor, getFindingFamilies, severityColor } from '../lib/score'

interface FindingsListProps {
  audit: {
    static_analysis?: ToolResult[]
    test_analysis?: ToolResult[]
    repository_analysis?: ToolResult[]
  }
}

function buildCodeGroups(
  instances: ReturnType<typeof getFindingFamilies>[number]['instances']
) {
  const groups = new Map<
    string,
    { code?: string; message: string; count: number; locations: string[] }
  >()

  instances.forEach((instance) => {
    const key = instance.code || instance.message
    const existing = groups.get(key)
    const location = instance.file_path
      ? `${instance.file_path}${instance.line ? `:${instance.line}` : ''}`
      : ''

    if (existing) {
      existing.count += 1
      if (location) existing.locations.push(location)
    } else {
      groups.set(key, {
        code: instance.code,
        message: instance.message,
        count: 1,
        locations: location ? [location] : [],
      })
    }
  })

  return groups
}

const USER_FILTERS = ['all', 'must_fix', 'important', 'minor']
const TECHNICAL_FILTERS = ['critical', 'high', 'medium', 'low', 'unknown']

function filterLabel(filter: string): string {
  return filter.replace(/_/g, ' ')
}

function matchesUserFilter(severity: string, filter: string): boolean {
  const normalized = severity.toLowerCase()
  if (filter === 'all') return true
  if (filter === 'must_fix') return normalized === 'critical' || normalized === 'high'
  if (filter === 'important') return normalized === 'medium'
  return normalized === 'low' || normalized === 'info' || normalized === 'unknown'
}

export function FindingsList({ audit }: FindingsListProps) {
  const families = getFindingFamilies(audit).filter((f) => f.count > 0)
  const [severityFilter, setSeverityFilter] = useState('all')
  const [showCodes, setShowCodes] = useState(false)

  if (families.length === 0) {
    return (
      <section className="rounded-2xl border border-health/25 bg-health/5 p-4">
        <div className="text-xs font-medium uppercase tracking-[0.16em] text-health">
          Findings
        </div>
        <p className="mt-2 text-sm leading-6 text-muted">
          No analyzer findings were returned from the evidence DrRepo could verify.
        </p>
      </section>
    )
  }

  const visibleFamilies =
    USER_FILTERS.includes(severityFilter)
      ? families.filter((family) => matchesUserFilter(family.severity, severityFilter))
      : severityFilter === 'all'
      ? families
      : families.filter((family) => family.severity.toLowerCase() === severityFilter)
  const totalFindings = families.reduce((sum, family) => sum + family.count, 0)

  return (
    <section className="rounded-2xl border border-border bg-surface p-4 animate-fade-up [animation-delay:180ms]">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
            Findings
          </h3>
          <p className="mt-1 text-sm text-muted">
            {totalFindings} grouped {totalFindings === 1 ? 'finding' : 'findings'} across {families.length} area{families.length === 1 ? '' : 's'}.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCodes((value) => !value)}
          className="inline-flex min-h-9 items-center justify-center rounded-xl border border-border px-3 text-xs font-medium text-muted transition-colors hover:border-brand/30 hover:text-brand"
        >
          {showCodes ? 'Hide codes' : 'Show codes'}
        </button>
      </div>

      <div className="mb-3 flex flex-wrap gap-2" aria-label="Filter issues by priority">
        {USER_FILTERS.map((filter) => (
          <button
            key={filter}
            type="button"
            aria-pressed={severityFilter === filter}
            onClick={() => setSeverityFilter(filter)}
            className={`min-h-8 rounded-full border px-3 text-[11px] font-medium capitalize transition-colors ${
              severityFilter === filter
                ? 'border-brand/30 bg-brand/10 text-brand'
                : 'border-border bg-base text-faint hover:text-primary'
              }`}
          >
            {filterLabel(filter)}
          </button>
        ))}
      </div>
      <details className="mb-4">
        <summary className="inline-flex min-h-8 cursor-pointer items-center text-xs text-muted transition-colors hover:text-primary">
          More filters
        </summary>
        <div className="mt-2 flex flex-wrap gap-2" aria-label="Filter findings by technical severity">
          {TECHNICAL_FILTERS.map((filter) => (
            <button
              key={filter}
              type="button"
              aria-pressed={severityFilter === filter}
              onClick={() => setSeverityFilter(filter)}
              className={`min-h-8 rounded-full border px-3 text-[11px] font-medium capitalize transition-colors ${
                severityFilter === filter
                  ? 'border-brand/30 bg-brand/10 text-brand'
                  : 'border-border bg-base text-faint hover:text-primary'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </details>

      {visibleFamilies.length === 0 ? (
        <p className="rounded-xl border border-border bg-base p-3 text-sm text-muted">
          No findings match this severity filter.
        </p>
      ) : (
        <div className="space-y-3">
          {visibleFamilies.map((family) => {
            const codeGroups = buildCodeGroups(family.instances)

            return (
              <article
                key={family.family}
                className={`rounded-2xl border-l-4 p-4 ${familyColor(family.family)}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded border px-2 py-1 text-[10px] font-medium uppercase ${severityColor(
                      family.severity
                    )}`}
                  >
                    {family.severity}
                  </span>
                  <h4 className="text-sm font-semibold text-primary">{family.family}</h4>
                  <span className="rounded-full bg-surface-2 px-2 py-1 text-[10px] text-faint">
                    {family.count} {family.count === 1 ? 'finding' : 'findings'}
                  </span>
                </div>

                <details className="mt-3">
                  <summary className="inline-flex min-h-9 cursor-pointer items-center rounded-lg text-xs text-muted transition-colors hover:text-primary">
                    Review grouped evidence
                  </summary>
                  <div className="mt-2 space-y-3">
                    {Array.from(codeGroups.values()).map((group) => {
                      const locPreview = [...new Set(group.locations)].slice(0, 4)
                      const moreCount = group.locations.length > 4 ? group.locations.length - 4 : 0

                      return (
                        <div key={`${group.code || group.message}`} className="rounded-xl border border-border bg-base p-3">
                          <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <p className="min-w-0 break-words text-sm leading-6 text-primary">
                              {group.message}
                            </p>
                            <span className="shrink-0 rounded-full bg-surface-2 px-2 py-1 text-[10px] font-mono text-faint">
                              {group.count}x
                            </span>
                          </div>
                          {showCodes && group.code && (
                            <div className="mt-2 break-all font-mono text-[10px] text-faint">
                              {group.code}
                            </div>
                          )}
                          {locPreview.length > 0 && (
                            <div className="mt-2 break-all font-mono text-[10px] leading-5 text-faint">
                              {locPreview.join(', ')}
                              {moreCount > 0 && ` +${moreCount} more`}
                            </div>
                          )}
                          <p className="mt-2 text-xs leading-5 text-muted">
                            Action: fix or justify this grouped pattern, then re-run the relevant analyzer.
                          </p>
                          <p className="mt-1 text-xs leading-5 text-faint">
                            Success check: this finding group no longer appears, or an intentional exception is documented.
                          </p>
                        </div>
                      )
                    })}
                  </div>
                </details>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
