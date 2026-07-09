import type { ToolResult } from '../types/api'
import { statusColor } from '../lib/score'

interface AnalyzerStatusGridProps {
  sections?: {
    static_analysis?: ToolResult[]
    test_analysis?: ToolResult[]
    repository_analysis?: ToolResult[]
  }
}

export function AnalyzerStatusGrid({ sections }: AnalyzerStatusGridProps) {
  const entries: { section: string; result: ToolResult }[] = []
  if (sections?.static_analysis) {
    sections.static_analysis.forEach((r) => entries.push({ section: 'static', result: r }))
  }
  if (sections?.test_analysis) {
    sections.test_analysis.forEach((r) => entries.push({ section: 'test', result: r }))
  }
  if (sections?.repository_analysis) {
    sections.repository_analysis.forEach((r) =>
      entries.push({ section: 'repository', result: r })
    )
  }

  if (entries.length === 0) return null

  return (
    <section className="animate-fade-up [animation-delay:120ms] rounded-lg border border-border bg-surface-2 p-4">
      <h3 className="text-xs font-medium text-muted mb-3">Evidence coverage</h3>
      <div className="flex flex-wrap gap-2">
        {entries.map(({ section, result }) => (
          <div
            key={`${section}-${result.tool}`}
            className={`inline-flex items-center gap-2 rounded-full border px-2 py-1 ${statusColor(result.status)}`}
          >
            <span className="text-xs font-medium capitalize">{result.tool}</span>
            <span className="h-1 w-1 rounded-full bg-current opacity-40" />
            <span className="text-[10px] uppercase tracking-wide">{result.status}</span>
            <span className="text-[9px] text-faint/70 capitalize">{section}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
