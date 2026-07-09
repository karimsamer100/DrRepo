import type { AuditMetadata } from '../types/api'

interface MetadataCardProps {
  metadata?: AuditMetadata
}

export function MetadataCard({ metadata }: MetadataCardProps) {
  if (!metadata) return null

  const items = [
    { label: 'Files', value: metadata.total_files },
    { label: 'Python files', value: metadata.python_files },
    { label: 'Test files', value: metadata.test_files },
    { label: 'Directories', value: metadata.total_directories },
  ].filter((item) => typeof item.value === 'number')

  if (items.length === 0 && metadata.has_readme === undefined) return null

  return (
    <section className="rounded-lg border border-border bg-surface-2 p-4">
      <h3 className="text-xs font-medium text-muted mb-3">Repository metadata</h3>
      {items.length > 0 && (
        <div className="grid grid-cols-2 gap-3 mb-3">
          {items.map((item) => (
            <div key={item.label}>
              <div className="text-[11px] font-medium uppercase tracking-wider text-faint">{item.label}</div>
              <div className="text-sm font-mono text-primary">{item.value}</div>
            </div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2 text-[11px] text-muted">
        {metadata.has_readme !== undefined && (
          <span>{metadata.has_readme ? 'README present' : 'No README'}</span>
        )}
        {metadata.has_tests !== undefined && (
          <span>{metadata.has_tests ? 'Tests folder' : 'No tests folder'}</span>
        )}
        {metadata.has_docs !== undefined && (
          <span>{metadata.has_docs ? 'Docs folder' : 'No docs folder'}</span>
        )}
        {metadata.has_pyproject !== undefined && (
          <span>{metadata.has_pyproject ? 'pyproject.toml' : 'No pyproject.toml'}</span>
        )}
        {metadata.has_gitignore !== undefined && (
          <span>{metadata.has_gitignore ? '.gitignore' : 'No .gitignore'}</span>
        )}
      </div>
    </section>
  )
}
