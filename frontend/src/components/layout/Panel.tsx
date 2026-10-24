import type { ReactNode } from 'react'

export function ExpandIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M6.5 2.5H3v3.5M9.5 2.5H13v3.5M6.5 13.5H3V10M9.5 13.5H13V10" fill="none" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  )
}

export default function Panel({
  title,
  state,
  expandLabel,
  onExpand,
  children,
  testId,
  className = '',
}: {
  title: string
  state: string
  expandLabel: string
  onExpand: () => void
  children: ReactNode
  testId?: string
  className?: string
}) {
  return (
    <section className={`panel ${className}`.trim()} data-testid={testId}>
      <header className="panel-head">
        <button type="button" className="panel-title" onClick={onExpand}>
          {title}
        </button>
        <span className="state-pill" data-state={state}>{state}</span>
        <button
          type="button"
          className="expand-btn"
          aria-label={`Expand ${expandLabel}`}
          title={`Expand ${expandLabel}`}
          onClick={onExpand}
        >
          <ExpandIcon />
        </button>
      </header>
      <div className="panel-body">{children}</div>
    </section>
  )
}
