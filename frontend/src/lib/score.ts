import type { AnalyzerStatus, Severity, ToolResult } from '../types/api'

export interface FindingFamilyInstance {
  tool: string
  section: string
  message: string
  code?: string
  file_path?: string
  line?: number
  column?: number
}

export interface FindingFamily {
  family: string
  severity: string
  count: number
  instances: FindingFamilyInstance[]
}

export function scoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'text-muted'
  if (score >= 85) return 'text-health'
  if (score >= 70) return 'text-attention'
  if (score >= 50) return 'text-warning'
  return 'text-error'
}

export function scoreBgColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'bg-surface-2'
  if (score >= 85) return 'bg-health/10 border-health/30'
  if (score >= 70) return 'bg-attention/10 border-attention/30'
  if (score >= 50) return 'bg-warning/10 border-warning/30'
  return 'bg-error/10 border-error/30'
}

export function severityColor(severity?: Severity | string): string {
  switch ((severity || '').toLowerCase()) {
    case 'critical':
      return 'text-critical bg-critical/10 border-critical/30'
    case 'high':
      return 'text-error bg-error/10 border-error/30'
    case 'medium':
      return 'text-warning bg-warning/10 border-warning/30'
    case 'low':
      return 'text-muted bg-muted/10 border-muted/30'
    default:
      return 'text-faint bg-surface-2 border-border'
  }
}

export function statusColor(status?: AnalyzerStatus | string): string {
  switch (status) {
    case 'completed':
      return 'bg-health/10 text-health border-health/30'
    case 'partial':
      return 'bg-warning/10 text-warning border-warning/30'
    case 'failed_to_run':
      return 'bg-error/10 text-error border-error/30'
    case 'not_available':
    case 'not_applicable':
    case 'skipped_by_config':
      return 'bg-surface-2 text-faint border-border'
    default:
      return 'bg-surface-2 text-muted border-border'
  }
}

export function labelForScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'unknown'
  if (score >= 85) return 'healthy'
  if (score >= 70) return 'needs attention'
  if (score >= 50) return 'needs improvement'
  return 'needs major improvement'
}

export function familyForTool(tool: string): string {
  const map: Record<string, string> = {
    readme: 'README documentation',
    structure: 'Structure & reproducibility',
    pytest: 'Testing failures',
    coverage: 'Coverage limitations',
    bandit: 'Security findings',
    ruff: 'Static analysis issues',
    radon: 'Complexity & maintainability',
  }
  return map[tool.toLowerCase()] || 'Other issues'
}

export function familyColor(family: string): string {
  switch (family) {
    case 'Security findings':
      return 'border-error/40 bg-error/5'
    case 'Testing failures':
      return 'border-warning/40 bg-warning/5'
    case 'README documentation':
    case 'Structure & reproducibility':
      return 'border-attention/40 bg-attention/5'
    case 'Coverage limitations':
    case 'Complexity & maintainability':
    case 'Other issues':
    default:
      return 'border-muted/30 bg-surface-2'
  }
}

function severityRank(severity?: string): number {
  const s = (severity || '').toLowerCase()
  if (s === 'critical') return 5
  if (s === 'high') return 4
  if (s === 'medium') return 3
  if (s === 'low') return 2
  return 1
}

export function getFindingFamilies(audit: {
  static_analysis?: ToolResult[]
  test_analysis?: ToolResult[]
  repository_analysis?: ToolResult[]
}): FindingFamily[] {
  const groups = new Map<string, FindingFamily>()

  const sections = [
    { label: 'Static analysis', items: audit.static_analysis || [] },
    { label: 'Test analysis', items: audit.test_analysis || [] },
    { label: 'Repository analysis', items: audit.repository_analysis || [] },
  ]

  sections.forEach((group) => {
    group.items.forEach((tool) => {
      ;(tool.findings || []).forEach((finding) => {
        const family = familyForTool(finding.tool || tool.tool)
        const existing = groups.get(family)
        const instance: FindingFamilyInstance = {
          tool: finding.tool || tool.tool,
          section: group.label,
          message: finding.message,
          code: finding.code,
          file_path: finding.file_path,
          line: finding.line,
          column: finding.column,
        }

        if (existing) {
          existing.count += 1
          existing.instances.push(instance)
          if (severityRank(finding.severity) > severityRank(existing.severity)) {
            existing.severity = finding.severity || 'unknown'
          }
        } else {
          groups.set(family, {
            family,
            severity: finding.severity || 'unknown',
            count: 1,
            instances: [instance],
          })
        }
      })
    })
  })

  return Array.from(groups.values())
}

export function attentionAreaFromFlag(flag: string): string {
  if (flag.includes('README')) return 'README documentation'
  if (flag.includes('STRUCTURE')) return 'Structure & reproducibility'
  if (flag.includes('TEST')) return 'Testing failures'
  if (flag.includes('SECURITY')) return 'Security findings'
  if (flag.includes('ANALYZER')) return 'Analyzer errors'
  return flag.replace(/_/g, ' ').toLowerCase()
}
