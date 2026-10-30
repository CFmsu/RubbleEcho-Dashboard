import Panel from '../layout/Panel'
import SensorCountdown from './SensorCountdown'
import type { OpenDialog } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import RangeLane from './RangeLane'
import { panelState } from './format'
import SignalScope from './SignalScope'

export default function SignalWall({
  snapshot,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  onOpen: OpenDialog
}) {
  const ultrasonic = snapshot?.ultrasonic
  const acoustic = snapshot?.acoustic
  const trace = snapshot?.rover_trace
  return (
    <>
      <Panel
        className="wave-card"
        title="Ultrasonic"
        state={panelState(ultrasonic?.source_mode)}
        expandLabel="ultrasonic reading"
        onExpand={() => onOpen({ kind: 'ultrasonic' })}
      >
        <p className="wave-value">{ultrasonic?.distance_cm == null ? '—' : ultrasonic.distance_cm}<small> cm</small></p>
        <div className="wave-figure">
          <RangeLane distanceCm={ultrasonic?.distance_cm ?? null} echoTimeout={Boolean(ultrasonic?.echo_timeout)} />
        </div>
        <SensorCountdown snapshot={snapshot} sensor="ultrasonic" />
        <p className="quiet-line">{ultrasonic ? `${ultrasonic.direction} · ${ultrasonic.quality}` : 'Waiting for an echo'} · amber is inside the 20 cm stop</p>
      </Panel>
      <Panel
        className="wave-card"
        title="Microphone"
        state={panelState(acoustic?.source_mode ?? 'live')}
        expandLabel="microphone reading"
        onExpand={() => onOpen({ kind: 'audio' })}
      >
        <p className="wave-value">{acoustic?.class ?? 'Listening'}</p>
        <div className="wave-figure">
          <SignalScope samples={snapshot?.acoustic_waveform ?? []} label="Acoustic waveform" instrument color="#2563eb" />
        </div>
        <p className="quiet-line">Microphone available{acoustic?.sound_category ? ` · ${acoustic.sound_category}` : ''}</p>
      </Panel>
      <Panel
        className="wave-card"
        title="Rover"
        state={panelState(trace?.source_mode ?? 'live')}
        expandLabel="rover reading"
        onExpand={() => onOpen({ kind: 'rover' })}
      >
        <p className="wave-value">{trace ? `${trace.left_counts}` : '—'}<small>{trace ? ` / ${trace.right_counts}` : ''}</small></p>
        <div className="wave-figure">
          <SignalScope
            samples={trace?.left ?? []}
            secondary={trace?.right ?? []}
            label="Left and right encoder ticks"
            instrument
            color="#2563eb"
            secondaryColor="#b45309"
          />
        </div>
        <SensorCountdown snapshot={snapshot} sensor="rover pose" />
        <p className="quiet-line">{trace ? 'Left in blue, right in amber' : 'No encoder sample. Motion follows the drive command.'}</p>
      </Panel>
    </>
  )
}
