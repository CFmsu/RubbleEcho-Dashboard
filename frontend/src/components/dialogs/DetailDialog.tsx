import type { ReactNode } from 'react'
import { sendEstop } from '../../api/operations'
import Modal from '../ui/Modal'

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
  return (
    <Modal
      open={open}
      title={title}
      state={state}
      onClose={onClose}
      dismissOnBackdrop={dismissOnBackdrop}
      headerActions={
        <button type="button" className="stop-btn dialog-stop" onClick={() => void sendEstop()}>
          STOP
        </button>
      }
    >
      {children}
    </Modal>
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
