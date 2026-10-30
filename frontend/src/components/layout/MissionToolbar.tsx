import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'

export default function MissionToolbar({
  snapshot,
  hasToken,
  status,
  onOpen,
  onManual,
}: {
  snapshot: OperationsSnapshot | null
  hasToken: boolean
  status: string
  onOpen: OpenDialog
  onManual: () => void
}) {
  const trial = snapshot?.trial_id ? snapshot.trial_id : 'No trial'
  const phase = snapshot?.run_active ? snapshot.scan_stage ?? 'SCANNING' : snapshot?.mission_phase ?? 'IDLE'
  const canExport = Boolean(snapshot?.trial_id)
  const elapsed = snapshot?.run_elapsed_s != null && (snapshot.run_active || snapshot.mission_phase === 'COMPLETE') ? `${Math.round(snapshot.run_elapsed_s)}s` : '—'
  const meta = `${trial} · ${phase} · runtime ${elapsed}`
  void hasToken

  return (
    <div className="mission-toolbar" data-testid="mission-toolbar">
      <p className="toolbar-meta" title={status ? `${meta} · ${status}` : meta}>
        {meta}{status ? ` · ${status}` : ''}
      </p>
      <div className="toolbar-actions">
        <button type="button" className="btn" onClick={onManual}>Manual control</button>
        <span title={canExport ? 'Choose ZIP, JSON, or CSV.' : 'Disabled until a trial is open.'}>
          <button type="button" className="btn" disabled={!canExport} onClick={() => onOpen({ kind: 'export' })}>Export</button>
        </span>
      </div>
    </div>
  )
}
