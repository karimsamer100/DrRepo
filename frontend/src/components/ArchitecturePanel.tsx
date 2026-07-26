import type { ArchitectureAssessment, ArchitectureEdge, ArchitectureNode, RiskHotspot } from '../types/api'

function toneForRisk(level?: string) {
  switch (level) {
    case 'critical':
    case 'high':
      return 'border-error/30 bg-error/5 text-error'
    case 'medium':
      return 'border-warning/30 bg-warning/5 text-warning'
    default:
      return 'border-border bg-base text-muted'
  }
}

function nodeById(nodes: ArchitectureNode[]) {
  return new Map(nodes.map((node) => [node.id, node]))
}

function LayerMap({ assessment }: { assessment: ArchitectureAssessment }) {
  const lookup = nodeById(assessment.nodes || [])
  const visibleLayers = (assessment.layers || []).filter((layer) => layer.node_ids?.length)
  const visibleEdges = (assessment.edges || []).slice(0, 24)

  if (!visibleLayers.length) {
    return <p className="text-sm text-muted">No architecture layers were detected from static evidence.</p>
  }

  const edgeLabel = (edge: ArchitectureEdge) => {
    const source = lookup.get(edge.source)?.label || edge.source.replace(/^node:/, '')
    const target = lookup.get(edge.target)?.label || edge.target.replace(/^node:/, '')
    return `${source} -> ${target}`
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
      <div className="grid gap-3 sm:grid-cols-2">
        {visibleLayers.slice(0, 8).map((layer) => (
          <section key={layer.id} className="rounded-2xl border border-border bg-base/60 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-primary">{layer.label}</h3>
              <span className="shrink-0 rounded-full border border-border px-2 py-0.5 text-[12px] uppercase tracking-[0.1em] text-faint">
                {layer.confidence || 'medium'}
              </span>
            </div>
            <div className="mt-3 space-y-2">
              {(layer.node_ids || []).slice(0, 5).map((nodeId) => {
                const node = lookup.get(nodeId)
                if (!node) return null
                return (
                  <div key={node.id} className="min-w-0 rounded-xl border border-border/70 bg-surface px-3 py-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium text-primary">{node.label}</span>
                      <span className="shrink-0 text-[11px] text-faint">{node.kind}</span>
                    </div>
                    <div className="mt-1 truncate font-mono text-[11px] text-faint">{node.path}</div>
                  </div>
                )
              })}
            </div>
          </section>
        ))}
      </div>
      <section className="rounded-2xl border border-border bg-base/60 p-4">
        <h3 className="text-sm font-semibold text-primary">Dependency Evidence</h3>
        <div className="mt-3 max-h-80 space-y-2 overflow-auto pr-1">
          {visibleEdges.length ? (
            visibleEdges.map((edge, index) => (
              <div key={`${edge.source}-${edge.target}-${index}`} className="rounded-xl border border-border/70 bg-surface px-3 py-2">
                <div className="text-xs font-medium text-primary">{edgeLabel(edge)}</div>
                <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-faint">
                  <span>{edge.kind}</span>
                  <span>{edge.confidence || 'medium'}</span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted">No internal dependency edges were detected.</p>
          )}
        </div>
      </section>
    </div>
  )
}

function HotspotCard({ hotspot }: { hotspot: RiskHotspot }) {
  return (
    <article className="rounded-2xl border border-border bg-base/60 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-faint">#{hotspot.rank} hotspot</div>
          <h3 className="mt-1 break-words text-base font-semibold text-primary">{hotspot.path}</h3>
          <p className="mt-2 text-sm leading-6 text-muted">{hotspot.why_it_matters}</p>
        </div>
        <div className={`shrink-0 rounded-xl border px-3 py-2 text-right ${toneForRisk(hotspot.risk_level)}`}>
          <div className="text-lg font-semibold">{hotspot.risk_score}</div>
          <div className="text-[12px] uppercase tracking-[0.1em]">{hotspot.risk_level}</div>
        </div>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-faint">Factors</div>
          <div className="mt-2 space-y-2">
            {(hotspot.factors || []).slice(0, 5).map((factor) => (
              <div key={factor.id} className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-surface px-3 py-2 text-sm">
                <span className="text-muted">{factor.label}</span>
                <span className="font-mono text-xs text-primary">+{factor.contribution}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-faint">Action</div>
          <p className="mt-2 text-sm leading-6 text-muted">{hotspot.recommended_action}</p>
          <div className="mt-3 rounded-xl border border-border/70 bg-surface px-3 py-2 text-xs text-faint">
            Test evidence: {hotspot.test_status || 'unknown'}
          </div>
        </div>
      </div>
    </article>
  )
}

export function ArchitecturePanel({ assessment }: { assessment?: ArchitectureAssessment }) {
  if (!assessment) return null
  const significantHotspots = (assessment.hotspots || []).filter((hotspot) =>
    ['critical', 'high', 'medium'].includes(hotspot.risk_level)
  )
  const hotspotHeading = significantHotspots.length > 0 ? 'Top risk hotspots' : 'Architecture review areas'

  return (
    <section className="rounded-2xl border border-border bg-surface p-5 shadow-card sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-faint">Architecture intelligence</div>
          <h2 className="mt-1 text-lg font-semibold text-primary">Static map and risk hotspots</h2>
        </div>
        <div className="rounded-full border border-border px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-faint">
          {assessment.status} / {assessment.confidence}
        </div>
      </div>
      <p className="mt-4 text-sm leading-6 text-muted">{assessment.summary}</p>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-border bg-base/60 p-3">
          <div className="text-[11px] uppercase tracking-[0.14em] text-faint">Entry points</div>
          <div className="mt-1 text-xl font-semibold text-primary">{assessment.entry_points?.length || 0}</div>
        </div>
        <div className="rounded-xl border border-border bg-base/60 p-3">
          <div className="text-[11px] uppercase tracking-[0.14em] text-faint">Cycles</div>
          <div className="mt-1 text-xl font-semibold text-primary">{assessment.cycles?.length || 0}</div>
        </div>
        <div className="rounded-xl border border-border bg-base/60 p-3">
          <div className="text-[11px] uppercase tracking-[0.14em] text-faint">Hotspots</div>
          <div className="mt-1 text-xl font-semibold text-primary">{assessment.hotspots?.length || 0}</div>
        </div>
      </div>

      <div className="mt-6">
        <LayerMap assessment={assessment} />
      </div>

      {!!assessment.hotspots?.length && (
        <div className="mt-6 space-y-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-faint">{hotspotHeading}</div>
          {significantHotspots.length === 0 && (
            <p className="text-sm leading-6 text-muted">
              No significant architecture hotspot was detected; these are lower-priority review areas from static evidence.
            </p>
          )}
          {assessment.hotspots.slice(0, 5).map((hotspot) => (
            <HotspotCard key={hotspot.id} hotspot={hotspot} />
          ))}
        </div>
      )}

      {!!assessment.evidence_gaps?.length && (
        <details className="mt-5 rounded-xl border border-border bg-base/60 p-4">
          <summary className="cursor-pointer text-sm font-medium text-primary">Evidence gaps and limitations</summary>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-muted">
            {assessment.evidence_gaps.slice(0, 5).map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
            {(assessment.limitations || []).slice(0, 3).map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
