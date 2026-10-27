import type { OperationsSnapshot } from '../../types/operations'
import { panelState } from '../live/format'
import SignalScope from '../live/SignalScope'
import DetailDialog, { FactGrid } from './DetailDialog'

export default function VibrationDetailDialog({
  open,
  snapshot,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  onClose: () => void
}) {
  const piezo = snapshot?.piezo
  const wave = snapshot?.piezo_waveform ?? []
  return (
    <DetailDialog open={open} onClose={onClose} title="Piezo contact" state={panelState(piezo?.source_mode)}>
      <SignalScope samples={wave} label="Piezo contact waveform in ADC counts" color="#b45309" large />
      <FactGrid
        rows={[
          ['Peak', piezo ? `${piezo.peak_adc_counts} ${piezo.unit}` : '—'],
          ['RMS', piezo ? `${piezo.rms_adc_counts} ${piezo.unit}` : '—'],
          ['Contact', piezo?.contact_state ?? 'No contact sample'],
          ['Site', piezo?.site_id ?? '—'],
          ['Clipped', piezo ? (piezo.clipped ? 'yes' : 'no') : '—'],
          ['Acceleration', 'not measured'],
          ['Source', piezo?.source_mode ?? 'unavailable'],
        ]}
      />
      <p className="quiet-line">The trace is the ADC window for this stop. A knock rings down. A quiet contact stays small. Counts are not acceleration in g.</p>
      <p className="quiet-line">Couple the disk to the plywood at a stop. A live PIEZO line with samples fills this same trace.</p>
    </DetailDialog>
  )
}
