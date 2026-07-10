export type AnalyzerStatus =
  | 'completed'
  | 'not_available'
  | 'not_applicable'
  | 'skipped_by_config'
  | 'failed_to_run'
  | 'partial'

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'unknown'

export interface ToolFinding {
  tool: string
  message: string
  file_path?: string
  line?: number
  column?: number
  severity?: Severity | string
  code?: string
}

export interface ToolResult {
  tool: string
  status: AnalyzerStatus
  summary?: Record<string, unknown>
  findings?: ToolFinding[]
  errors?: string[]
  raw_output?: string | null
}

export interface ScoreBreakdown {
  score: number
  finding_count?: number
  penalty?: number
  status_counts?: Record<string, number>
}

export interface AuditScoring {
  overall_score: number
  repository_health_score?: number
  portfolio_readiness_score?: number
  sections?: {
    static_analysis?: ScoreBreakdown
    test_analysis?: ScoreBreakdown
    repository_analysis?: ScoreBreakdown
  }
  categories?: {
    code_quality?: number
    testing?: number
    security?: number
    maintainability?: number
    documentation?: number
    structure?: number
  }
}

export interface RepositoryHealth {
  label?: string
  score?: number | null
  summary?: string
}

export interface Diagnosis {
  repository_health?: RepositoryHealth
  hard_flags?: string[]
  limitations?: string[]
}

export interface RemediationSuggestion {
  severity?: string
  section?: string
  tool?: string
  title?: string
  action?: string
}

export interface AuditMetadata {
  total_files?: number
  total_directories?: number
  python_files?: number
  test_files?: number
  has_readme?: boolean
  has_tests?: boolean
  has_docs?: boolean
  has_pyproject?: boolean
  has_gitignore?: boolean
  [key: string]: unknown
}

export interface Audit {
  status?: string
  path?: string
  metadata?: AuditMetadata
  static_analysis?: ToolResult[]
  test_analysis?: ToolResult[]
  repository_analysis?: ToolResult[]
  scoring?: AuditScoring
  diagnosis?: Diagnosis
  remediation_suggestions?: RemediationSuggestion[]
  remediation_summary?: {
    total?: number
    by_severity?: Record<string, number>
  }
}

export interface AdvisorAction {
  title?: string
  priority?: string
  why_it_matters?: string
  evidence?: string | string[]
}

export interface AdvisorResponse {
  summary?: string
  top_priorities?: AdvisorAction[]
  lower_priority_items?: AdvisorAction[]
  limitations?: string[]
  next_steps?: string[]
}

export interface AdvisorReport {
  advisor_report_version?: string
  profiled_action_plan?: {
    profile?: {
      display_name?: string
    }
    profile_fit_summary?: string
    top_priorities?: AdvisorAction[]
    lower_priority_items?: AdvisorAction[]
    [key: string]: unknown
  }
  advisor_response?: AdvisorResponse
  markdown_section?: string
  summary_lines?: string[]
}

export type SourceType = 'local_path' | 'github_url'

export interface AuditRequest {
  source_type: SourceType
  source_value: string
  profile_id: string
  ai: false
  include_markdown: boolean
}

export interface AuditResponse {
  status: string
  source_type: string
  source_value: string
  profile_id: string
  audit: Audit
  advisor: AdvisorReport | null
  markdown: string | null
}

export interface ProfileInfo {
  profile_id: string
  display_name: string
  description: string
}

export interface HealthCheckResponse {
  status: string
  version: string
}
