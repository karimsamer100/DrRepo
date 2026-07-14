import type { AuditMetadata } from '../types/api'

interface MetadataCardProps {
  metadata?: AuditMetadata
  dependencyEnvironment?: {
    detected_dependency_strategy?: string
    dependency_metadata_exists?: boolean
    lock_file_exists?: boolean
    likely_install_command?: string | null
  }
}

function PresenceChip({ label, present }: { label: string; present?: boolean }) {
  if (present === undefined) return null
  return (
    <span
      className={`rounded-full border px-2 py-1 text-[10px] font-medium ${
        present
          ? 'border-health/25 bg-health/10 text-health'
          : 'border-warning/30 bg-warning/10 text-warning'
      }`}
    >
      {present ? label : `Missing ${label}`}
    </span>
  )
}

export function MetadataCard({ metadata, dependencyEnvironment }: MetadataCardProps) {
  if (!metadata) return null

  const items = [
    { label: 'Files', value: metadata.total_files },
    { label: 'Python files', value: metadata.python_files },
    { label: 'Test files', value: metadata.test_files },
    { label: 'Directories', value: metadata.total_directories },
  ].filter((item) => typeof item.value === 'number')

  if (items.length === 0 && metadata.has_readme === undefined) return null

  return (
    <section className="rounded-2xl border border-border bg-surface p-4">
      <h3 className="mb-3 text-xs font-medium uppercase tracking-[0.16em] text-faint">
        Repository metadata
      </h3>
      {items.length > 0 && (
        <div className="mb-4 grid grid-cols-2 gap-3">
          {items.map((item) => (
            <div key={item.label} className="rounded-xl border border-border bg-base p-3">
              <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-faint">{item.label}</div>
              <div className="mt-1 text-sm font-mono text-primary">{item.value}</div>
            </div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <PresenceChip label="README" present={metadata.has_readme} />
        <PresenceChip label="tests" present={metadata.has_tests} />
        <PresenceChip label="docs" present={metadata.has_docs} />
        <PresenceChip label="pyproject.toml" present={metadata.has_pyproject} />
        <PresenceChip label=".gitignore" present={metadata.has_gitignore} />
      </div>
      {dependencyEnvironment && (
        <div className="mt-4 rounded-xl border border-border bg-base p-3">
          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-faint">
            Dependency environment
          </div>
          <p className="mt-1 text-xs leading-5 text-muted">
            Strategy: {dependencyEnvironment.detected_dependency_strategy || 'unknown'}.
            Lock file: {dependencyEnvironment.lock_file_exists ? 'yes' : 'no'}.
          </p>
          {dependencyEnvironment.likely_install_command && (
            <code className="mt-2 block break-all font-mono text-[10px] text-faint">
              {dependencyEnvironment.likely_install_command}
            </code>
          )}
        </div>
      )}
    </section>
  )
}
