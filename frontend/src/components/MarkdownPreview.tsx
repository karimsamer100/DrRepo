interface MarkdownPreviewProps {
  content: string | null
}

export function MarkdownPreview({ content }: MarkdownPreviewProps) {
  if (!content) return null

  return (
    <section className="animate-fade-up [animation-delay:300ms]">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10px] font-semibold uppercase tracking-wider text-faint">
          Markdown report
        </h3>
        <button
          type="button"
          onClick={() => navigator.clipboard?.writeText(content)}
          className="text-[11px] text-muted hover:text-primary transition-colors"
        >
          Copy
        </button>
      </div>
      <div className="rounded-lg border border-border bg-surface-2 overflow-hidden max-w-full">
        <div className="flex items-center justify-between border-b border-border bg-base px-3 py-1.5">
          <span className="font-mono text-[11px] text-faint">REPORT.md</span>
        </div>
        <pre className="p-3 font-mono text-xs leading-relaxed text-primary whitespace-pre-wrap overflow-auto max-h-[70vh]">
          {content}
        </pre>
      </div>
    </section>
  )
}
