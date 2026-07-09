export function LoadingState() {
  return (
    <div className="w-full max-w-lg mx-auto animate-fade-up">
      <div className="rounded-xl border border-border bg-surface p-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <svg
            className="h-8 w-8 text-brand animate-[shimmer_2s_ease-in-out_infinite]"
            viewBox="0 0 28 28"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <rect x="1" y="1" width="26" height="26" rx="5" stroke="currentColor" strokeWidth="2" />
            <path d="M14 7v14M7 14h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <div>
            <h2 className="text-base font-semibold text-white">Running diagnostic</h2>
            <p className="text-xs text-faint mt-0.5">Collecting repository evidence</p>
          </div>
        </div>
      </div>
    </div>
  )
}
