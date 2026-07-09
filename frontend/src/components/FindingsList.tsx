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

export function FindingsList({ audit }: FindingsListProps) {
  const families = getFindingFamilies(audit).filter((f) => f.count > 0)
  if (families.length === 0) return null

  return (
    <section className="animate-fade-up [animation-delay:180ms]">
      <h3 className="text-[10px] font-semibold uppercase tracking-wider text-faint mb-2">
        Findings
      </h3>
      <div className="space-y-2">
        {families.map((family) => {
          const codeGroups = buildCodeGroups(family.instances)
          const hasDetails = codeGroups.size > 1 || family.count > 1

          return (
            <div
              key={family.family}
              className={`rounded-lg border-l-4 bg-surface p-3 ${familyColor(family.family)}`}
            >
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span
                  className={`rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase ${severityColor(
                    family.severity
                  )}`}
                >
                  {family.severity}
                </span>
                <span className="text-sm font-medium text-primary">{family.family}</span>
                <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] text-faint">
                  {family.count} {family.count === 1 ? 'finding' : 'findings'}
                </span>
              </div>

              {!hasDetails && family.instances[0].file_path && (
                <div className="font-mono text-[11px] text-faint">
                  {family.instances[0].file_path}
                  {family.instances[0].line ? `:${family.instances[0].line}` : ''}
                </div>
              )}

              {hasDetails && (
                <details className="mt-2">
                  <summary className="text-[11px] text-muted cursor-pointer hover:text-primary transition-colors">
                    Details
                  </summary>
                  <ul className="mt-2 space-y-1.5 pl-1">
                    {Array.from(codeGroups.values()).map((group, i) => (
                      <li key={i} className="text-xs text-muted">
                        {group.code && (
                          <span className="font-mono text-[10px] text-faint mr-2">
                            {group.code}
                            {group.count > 1 && ` (${group.count})`}
                          </span>
                        )}
                        <span className="text-primary">{group.message}</span>
                        {group.locations.length > 0 && (
                          <span className="block mt-0.5 font-mono text-[10px] text-faint">
                            {group.locations.slice(0, 3).join(', ')}
                            {group.locations.length > 3 && ` +${group.locations.length - 3} more`}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
