import { useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { sendEstop } from '../../api/operations'

export default function DetailDialog({
  open,
  title,
  state,
  onClose,
  children,
  dismissOnBackdrop = true,
}: {
  open: boolean
  title: string
  state?: string
  onClose: () => void
  children: ReactNode
  dismissOnBackdrop?: boolean
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
    return () => {
      // Release the top layer if this instance goes away. Do not listen for
      // the resulting close event: StrictMode delivers it after the dialog
      // has already been shown again, and treating it as a user dismiss
      // unmounts the dialog immediately.
      if (dialog.open) dialog.close()
    }
  }, [open])

  const requestClose = () => onCloseRef.current()

  if (typeof document === 'undefined') return null

  return createPortal(
    <dialog
      ref={ref}
      className="detail-dialog"
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault()
        requestClose()
      }}
      onMouseDown={(event) => {
        if (!dismissOnBackdrop || !ref.current) return
        const bounds = ref.current.getBoundingClientRect()
        const inside =
          event.clientX >= bounds.left &&
          event.clientX <= bounds.right &&
          event.clientY >= bounds.top &&
          event.clientY <= bounds.bottom
        if (!inside) requestClose()
      }}
    >
      <header className="detail-head">
        <h2 id={titleId}>{title}</h2>
        {state ? <span className="state-pill" data-state={state}>{state}</span> : null}
        <button type="button" className="stop-btn dialog-stop" onClick={() => void sendEstop()}>
          STOP
        </button>
        <button type="button" className="icon-btn" aria-label="Close" onClick={requestClose}>
          ×
        </button>
      </header>
      <div className="detail-body">{children}</div>
    </dialog>,
    document.body,
  )
}

export function FactGrid({ rows }: { rows: Array<[string, string]> }) {
  return (
    <dl className="fact-grid">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}
