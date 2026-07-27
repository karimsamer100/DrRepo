interface DrRepoMarkProps {
  className?: string
  decorative?: boolean
  title?: string
}

export function DrRepoMark({ className = 'h-6 w-6', decorative = true, title = 'DrRepo mark' }: DrRepoMarkProps) {
  return (
    <img
      className={className}
      src="/brand/drrepo-favicon.png"
      alt={decorative ? '' : title}
      aria-hidden={decorative ? 'true' : undefined}
      draggable={false}
    />
  )
}
