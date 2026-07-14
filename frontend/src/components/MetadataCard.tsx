import type { AuditMetadata, ProjectUnderstanding } from '../types/api'

interface MetadataCardProps {
  metadata?: AuditMetadata
  dependencyEnvironment?: {
    detected_dependency_strategy?: string
    dependency_metadata_exists?: boolean
    lock_file_exists?: boolean
    likely_install_command?: string | null
  }
  projectUnderstanding?: ProjectUnderstanding
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

function CommandList({ title, commands }: { title: string; commands?: string[] }) {
  if (!commands || commands.length === 0) return null
  return (
    <div className="mt-2">
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-faint">{title}</div>
      <div className="mt-1 space-y-1">
        {commands.slice(0, 3).map((command) => (
          <code key={command} className="block break-all font-mono text-[10px] text-faint">
            {command}
          </code>
        ))}
      </div>
    </div>
  )
}

export function MetadataCard({ metadata, dependencyEnvironment, projectUnderstanding }: MetadataCardProps) {
  if (!metadata) return null
  const identity = projectUnderstanding?.project_identity
  const runnability = projectUnderstanding?.runnability
  const entryPoints = projectUnderstanding?.entry_points || []

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
      {identity && (
        <div className="mt-4 rounded-xl border border-border bg-base p-3">
          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-faint">
            Project identity
          </div>
          <p className="mt-1 text-xs leading-5 text-muted">
            {identity.project_type || 'Unknown project'} · {identity.package_layout || 'unknown layout'} · confidence {identity.confidence || 'unknown'}.
          </p>
          {(identity.frameworks?.length || identity.interfaces?.length) && (
            <div className="mt-2 flex flex-wrap gap-2">
              {[...(identity.frameworks || []), ...(identity.interfaces || [])].slice(0, 8).map((item) => (
                <span key={item} className="rounded-full border border-border bg-surface px-2 py-1 text-[10px] text-faint">
                  {item}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
      {runnability && (
        <div className="mt-4 rounded-xl border border-border bg-base p-3">
          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-faint">
            Runnability
          </div>
          <p className="mt-1 text-xs leading-5 text-muted">
            Status: {runnability.status || 'unknown'}. Confidence: {runnability.confidence || 'unknown'}.
          </p>
          <CommandList title="Install" commands={runnability.install_commands} />
          <CommandList title="Run" commands={runnability.run_commands} />
          <CommandList title="Test" commands={runnability.test_commands} />
        </div>
      )}
      {entryPoints.length > 0 && (
        <details className="mt-4 rounded-xl border border-border bg-base p-3">
          <summary className="cursor-pointer text-[10px] font-medium uppercase tracking-[0.14em] text-faint">
            Entry points
          </summary>
          <div className="mt-2 space-y-2">
            {entryPoints.slice(0, 5).map((entry) => (
              <div key={`${entry.kind}-${entry.path}-${entry.command}`} className="text-xs leading-5 text-muted">
                <span className="text-primary">{entry.kind || 'entry'}</span>: {entry.path}
                {entry.command && <code className="ml-1 font-mono text-[10px] text-faint">{entry.command}</code>}
              </div>
            ))}
          </div>
        </details>
      )}
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
