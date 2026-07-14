import type { ToolResult } from '../types/api'
import {
  evidenceTone,
  isEvidenceLimitation,
  resultStatusLabel,
  statusExplanation,
} from '../lib/presentation'

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

  const verified = entries.filter(({ result }) => result.status === 'completed')
  const limitations = entries.filter(({ result }) => isEvidenceLimitation(result.status))
  const analyzerErrors = entries.filter(({ result }) => result.status === 'failed_to_run')
  const partial = entries.filter(({ result }) => result.status === 'partial')

  return (
    <section className="rounded-2xl border border-border bg-surface p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-faint">
            Evidence coverage
          </h3>
          <p className="mt-1 text-xs leading-5 text-muted">
            {verified.length} of {entries.length} analyzers completed.
          </p>
        </div>
        <span className="rounded-full border border-border bg-base px-2 py-1 text-[10px] font-mono text-faint">
          {limitations.length + partial.length} limited
        </span>
      </div>

      <div className="space-y-2">
        {entries.map(({ section, result }) => (
          <details
            key={`${section}-${result.tool}`}
            className={`rounded-xl border px-3 py-2 ${evidenceTone(result)}`}
          >
            <summary className="flex min-h-8 cursor-pointer list-none items-center justify-between gap-3 text-xs [&::-webkit-details-marker]:hidden">
              <span className="min-w-0">
                <span className="font-mono font-medium">{result.tool}</span>
                <span className="ml-2 text-[10px] uppercase tracking-[0.14em] opacity-70">
                  {section}
                </span>
              </span>
              <span className="shrink-0 text-[10px] font-medium uppercase tracking-[0.12em]">
                {resultStatusLabel(result)}
              </span>
            </summary>
            <p className="mt-2 text-xs leading-5 text-muted">
              {statusExplanation(result)}
            </p>
            {result.errors && result.errors.length > 0 && result.status === 'failed_to_run' && (
              <pre className="mt-2 max-h-24 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-error/20 bg-base p-2 font-mono text-[10px] text-error/90">
                {result.errors.slice(0, 2).join('\n')}
              </pre>
            )}
          </details>
        ))}
      </div>

      {(limitations.length > 0 || analyzerErrors.length > 0) && (
        <p className="mt-4 border-t border-border pt-3 text-xs leading-5 text-faint">
          Unavailable or skipped optional tools reduce confidence. Only failed analyzer executions
          are treated as audit errors.
        </p>
      )}
    </section>
  )
}
