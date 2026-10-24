import { useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

export type ModalProps = {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  description?: string
  className?: string
  state?: string
  headerActions?: ReactNode
  dismissOnBackdrop?: boolean
}

export default function Modal({
  open,
  title,
  onClose,
  children,
  description,
  className = '',
  state,
  headerActions,
  dismissOnBackdrop = true,
}: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const descriptionId = useId()
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
      // Drop the top layer if this instance unmounts. The close event is not
      // treated as a user dismiss: StrictMode can deliver it after the next
      // showModal, which would immediately close the window.
      if (dialog.open) dialog.close()
    }
  }, [open])

  const requestClose = () => {
    const dialog = ref.current
    if (dialog?.open) dialog.close()
    onCloseRef.current()
  }

  if (typeof document === 'undefined' || !open) return null

  return createPortal(
    <dialog
      ref={ref}
      className="modal-overlay"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      onCancel={(event) => {
        event.preventDefault()
        requestClose()
      }}
      onMouseDown={(event) => {
        if (!dismissOnBackdrop) return
        const panel = ref.current?.querySelector('.modal-panel')
        if (panel && event.target instanceof Node && panel.contains(event.target)) return
        requestClose()
      }}
    >
      <div className="modal-dim" />
      <div className={`modal-panel ${className}`.trim()} data-testid="modal-panel">
        <header className="modal-head">
          <h2 id={titleId}>{title}</h2>
          {state ? <span className="state-pill" data-state={state}>{state}</span> : null}
          <div className="modal-head-actions">
            {headerActions}
            <button type="button" className="icon-btn modal-close" aria-label="Close" onClick={requestClose}>
              ×
            </button>
          </div>
        </header>
        {description ? <p id={descriptionId} className="visually-hidden">{description}</p> : null}
        <div className="modal-body">{children}</div>
      </div>
    </dialog>,
    document.body,
  )
}
