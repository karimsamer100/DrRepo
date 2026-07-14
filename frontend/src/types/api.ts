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
  duration_ms?: number | null
  execution_mode?: AnalysisMode | string | null
  skipped_reason?: string | null
  unavailable_reason?: string | null
  tool_version?: string | null
  analysis_outcome?: string | null
  evidence_impact?: string | null
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

export interface EvidenceConfidence {
  label?: 'full' | 'partial' | 'limited' | string
  summary?: string
  available_optional_tools?: string[]
  missing_optional_tools?: string[]
  skipped_optional_tools?: string[]
  failed_optional_tools?: string[]
  incomplete_optional_tools?: string[]
}

export interface Diagnosis {
  repository_health?: RepositoryHealth
  hard_flags?: string[]
  limitations?: string[]
  evidence_confidence?: EvidenceConfidence
}

export interface RemediationSuggestion {
  severity?: string
  section?: string
  tool?: string
  title?: string
  action?: string
}

export interface EvidenceItem {
  path: string
  reason: string
  detail?: string | null
}

export interface ProjectIdentity {
  primary_language?: string
  project_type?: string
  secondary_project_types?: string[]
  frameworks?: string[]
  interfaces?: string[]
  package_layout?: string
  confidence?: string
  evidence?: EvidenceItem[]
}

export interface ProjectEntryPoint {
  kind?: string
  path?: string
  symbol?: string | null
  command?: string | null
  confidence?: string
  evidence?: EvidenceItem[]
}

export interface ProjectRunnability {
  install_commands?: string[]
  run_commands?: string[]
  test_commands?: string[]
  build_commands?: string[]
  status?: string
  confidence?: string
  missing_requirements?: string[]
  evidence?: EvidenceItem[]
}

export interface ArchitectureSummary {
  backend_present?: boolean
  frontend_present?: boolean
  cli_present?: boolean
  api_present?: boolean
  ml_present?: boolean
  notebooks_present?: boolean
  database_signals?: string[]
  container_signals?: string[]
  ci_signals?: string[]
  important_directories?: string[]
}

export interface ProjectUnderstanding {
  project_identity?: ProjectIdentity
  entry_points?: ProjectEntryPoint[]
  runnability?: ProjectRunnability
  architecture_summary?: ArchitectureSummary
}

export interface ExecutiveReport {
  headline?: string
  one_sentence_summary?: string
  project_description?: string
  verdict?: string
  observed_score?: number | null
  evidence_confidence?: string
  strongest_signals?: string[]
  primary_risks?: string[]
  biggest_gap?: string
  next_best_step?: string
  evidence_gaps?: string[]
  user_profile_context?: string
}

export interface StructuredRecommendation {
  id?: string
  title?: string
  category?: string
  priority?: number
  severity?: string
  confidence?: string
  impact?: string
  effort?: string
  recommendation_type?: 'repository_fix' | 'audit_environment' | 'verification_step' | string
  why_it_matters?: string
  evidence?: string[]
  related_findings?: string[]
  recommended_steps?: string[]
  optional_example?: string | null
  success_check?: string
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
  source?: {
    type?: string
    value?: string
  }
  analysis?: {
    mode?: AnalysisMode | string
    source_type?: SourceType | string
    executes_repository_code?: boolean
  }
  dependency_environment?: {
    dependency_files?: string[]
    dependency_metadata_exists?: boolean
    lock_files?: string[]
    lock_file_exists?: boolean
    detected_dependency_strategy?: string
    likely_install_command?: string | null
    note?: string
  }
  metadata?: AuditMetadata
  static_analysis?: ToolResult[]
  test_analysis?: ToolResult[]
  repository_analysis?: ToolResult[]
  scoring?: AuditScoring
  diagnosis?: Diagnosis
  remediation_suggestions?: RemediationSuggestion[]
  recommendations_v2?: StructuredRecommendation[]
  project_understanding?: ProjectUnderstanding
  executive_report?: ExecutiveReport
  remediation_summary?: {
    total?: number
    by_severity?: Record<string, number>
  }
}

export interface AdvisorAction {
  title?: string
  action?: string
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
export type AnalysisMode = 'quick_safe' | 'deep_local'

export interface AuditRequest {
  source_type: SourceType
  source_value: string
  analysis_mode?: AnalysisMode | null
  profile_id: string
  ai: false
  include_markdown: boolean
}

export interface AuditResponse {
  status: string
  source_type: SourceType
  source_value: string
  analysis_mode: AnalysisMode
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

export interface AnalyzerCapability {
  analyzer_id: string
  display_name: string
  section: string
  category: string
  executes_repository_code: boolean
  supported_source_types: SourceType[]
  supported_analysis_modes: AnalysisMode[]
  available: boolean
  installed_version?: string | null
  unavailable_reason?: string | null
  default_timeout_seconds: number
  core: boolean
}

export interface AnalysisModeCapability {
  id: AnalysisMode
  display_name: string
  description: string
  executes_repository_code: boolean
  supported_source_types: SourceType[]
}

export interface CapabilitiesResponse {
  supported_analysis_modes: AnalysisModeCapability[]
  supported_source_types: SourceType[]
  analyzers: AnalyzerCapability[]
  docker_isolated_execution: {
    supported: boolean
    reason?: string
  }
  remote_execution_safety_policy: string
  setup: {
    analysis_extra?: string
    install_command?: string
  }
}
