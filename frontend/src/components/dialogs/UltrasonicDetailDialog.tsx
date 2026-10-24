import type { OperationsSnapshot } from '../../types/operations'
import { panelState } from '../live/format'
import DetailDialog, { FactGrid } from './DetailDialog'

export default function UltrasonicDetailDialog({
  open,
  snapshot,
  onClose,
}: {
  open: boolean
  snapshot: OperationsSnapshot | null
  onClose: () => void
}) {
  const range = snapshot?.ultrasonic
  return (
    <DetailDialog open={open} onClose={onClose} title="HC-SR04 obstacle distance" state={panelState(range?.source_mode)}>
      <p className="measure">{range?.distance_cm == null ? '—' : range.distance_cm}<small> cm</small></p>
      <FactGrid
        rows={[
          ['Direction', range?.direction ?? '—'],
          ['Quality', range?.quality ?? 'no sample'],
          ['Echo timeout', range ? (range.echo_timeout ? 'yes — path is not clear' : 'no') : '—'],
          ['Source', range?.source_mode ?? 'unavailable'],
          ['Meaning', 'Obstacle range in front of the sensor. Not depth through rubble.'],
          ['Stop margin', 'Configured policy, initial 20 cm, pending a measured rover. Not a reading.'],
        ]}
      />
    </DetailDialog>
  )
}
