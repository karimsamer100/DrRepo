import type { AnalyzerStatus, Audit, AuditResponse, SourceType, ToolResult } from '../types/api'

export interface EvidenceEntry {
  section: 'static' | 'test' | 'repository'
  result: ToolResult
}

export function sourceTypeLabel(sourceType?: string): string {
  return sourceType === 'github_url' ? 'Public GitHub repository' : 'Local repository'
}

export function compactSource(source: string): string {
  if (source.length <= 76) return source
  return `${source.slice(0, 34)}...${source.slice(-34)}`
}

export function collectEvidenceEntries(audit: Audit): EvidenceEntry[] {
  const entries: EvidenceEntry[] = []
  audit.static_analysis?.forEach((result) => entries.push({ section: 'static', result }))
  audit.test_analysis?.forEach((result) => entries.push({ section: 'test', result }))
  audit.repository_analysis?.forEach((result) => entries.push({ section: 'repository', result }))
  return entries
}

export function resultFindingCount(result?: ToolResult): number {
  return Array.isArray(result?.findings) ? result.findings.length : 0
}

export function resultStatusLabel(result?: ToolResult): string {
  const findingCount = resultFindingCount(result)
  switch (result?.status) {
    case 'completed':
      return findingCount > 0
        ? `Completed - ${findingCount} ${findingCount === 1 ? 'finding' : 'findings'}`
        : 'Verified clean'
    case 'partial':
      return 'Partial'
    case 'not_available':
      return 'Unavailable'
    case 'not_applicable':
      return 'Not applicable'
    case 'skipped_by_config':
      return 'Skipped'
    case 'failed_to_run':
      return 'Failed to run'
    default:
      return 'Unknown'
  }
}

export function statusExplanation(result?: ToolResult): string {
  switch (result?.status) {
    case 'completed':
      return resultFindingCount(result) > 0
        ? 'The analyzer ran successfully and reported findings that may affect repository quality.'
        : 'The analyzer ran successfully and reported no findings.'
    case 'partial':
      return 'DrRepo collected some evidence, but the analyzer could not complete every check.'
    case 'not_available':
      return 'The tool is not installed in the DrRepo environment. This is an evidence limitation, not a repository failure.'
    case 'not_applicable':
      return 'This check does not apply to the current repository or source mode.'
    case 'skipped_by_config':
      return result.skipped_reason || 'This check was intentionally skipped, commonly for remote audit safety.'
    case 'failed_to_run':
      return 'The analyzer tried to run and failed. Treat this as incomplete evidence unless it is a core analyzer.'
    default:
      return 'DrRepo did not provide a detailed status for this analyzer.'
  }
}

export function isEvidenceLimitation(status?: AnalyzerStatus | string): boolean {
  return status === 'not_available' || status === 'not_applicable' || status === 'skipped_by_config' || status === 'failed_to_run' || status === 'partial'
}

export function evidenceTone(result?: ToolResult): string {
  switch (result?.status) {
    case 'completed':
      return resultFindingCount(result) > 0
        ? 'border-attention/30 bg-attention/10 text-attention'
        : 'border-health/25 bg-health/10 text-health'
    case 'partial':
      return 'border-warning/30 bg-warning/10 text-warning'
    case 'failed_to_run':
      return 'border-error/30 bg-error/10 text-error'
    case 'not_available':
    case 'not_applicable':
    case 'skipped_by_config':
      return 'border-border bg-surface-2 text-faint'
    default:
      return 'border-border bg-surface-2 text-muted'
  }
}

export function categoryEvidenceState(category: string, data: AuditResponse): string | null {
  const entries = collectEvidenceEntries(data.audit)
  const lowerCategory = category.toLowerCase()
  const relevantTools: Record<string, string[]> = {
    code_quality: ['ruff'],
    security: ['bandit'],
    maintainability: ['radon', 'ruff'],
    testing: ['pytest', 'coverage'],
    documentation: ['readme'],
    structure: ['structure'],
  }
  const tools = relevantTools[lowerCategory] || []
  const relevant = entries.filter(({ result }) => tools.includes(result.tool.toLowerCase()))
  if (relevant.length === 0) return null

  if (relevant.some(({ result }) => result.status === 'failed_to_run')) return 'analyzer error'
  if (relevant.some(({ result }) => result.status === 'skipped_by_config')) return 'skipped evidence'
  if (relevant.some(({ result }) => result.status === 'not_available')) return 'limited evidence'
  if (relevant.some(({ result }) => result.status === 'partial')) return 'partial evidence'
  if (relevant.some(({ result }) => resultFindingCount(result) > 0)) return 'verified with findings'
  return 'verified clean'
}

export function formatVerdict(label?: string): string {
  return (label || 'unknown').replace(/_/g, ' ')
}

export function classifyError(error: string | null): {
  title: string
  summary: string
  detail?: string
  nextAction: string
} {
  const message = error || 'An unexpected error occurred.'
  const lower = message.toLowerCase()

  if (lower.includes('failed to fetch') || lower.includes('networkerror')) {
    return {
      title: 'DrRepo API is unreachable',
      summary: 'The browser could not reach the audit service.',
      detail: 'Confirm the FastAPI server is running and that VITE_API_BASE points to it.',
      nextAction: 'Check the API server, then try again.',
    }
  }

  if (lower.includes('invalid') && lower.includes('github')) {
    return {
      title: 'GitHub URL is not supported',
      summary: 'DrRepo accepts public github.com repository URLs.',
      detail: message,
      nextAction: 'Use a public https://github.com/owner/repo URL.',
    }
  }

  if (lower.includes('clone') || lower.includes('github')) {
    return {
      title: 'GitHub repository could not be audited',
      summary: 'DrRepo could not clone or read the public repository.',
      detail: message,
      nextAction: 'Check the URL and repository visibility, then try again.',
    }
  }

  if (lower.includes('path') || lower.includes('not found') || lower.includes('does not exist')) {
    return {
      title: 'Local repository path is invalid',
      summary: 'DrRepo could not find or read that local directory.',
      detail: message,
      nextAction: 'Enter a repository path that exists on the API server machine.',
    }
  }

  return {
    title: 'Diagnostic failed',
    summary: 'The audit service returned an error before producing a result.',
    detail: message,
    nextAction: 'Review the detail, adjust the input if needed, then try again.',
  }
}

export function shortSourceMode(sourceType: SourceType | string): string {
  return sourceType === 'github_url' ? 'GitHub' : 'Local'
}
