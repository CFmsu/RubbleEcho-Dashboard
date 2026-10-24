import type { OperationsSnapshot } from '../../types/operations'
import CameraColumn from './CameraColumn'
import ControlBar from './ControlBar'
import EventLog from './EventLog'
import LegacyPanel from './LegacyPanel'
import RadarScope from './RadarScope'
import ReasoningPanel from './ReasoningPanel'
import SandTableMap from './SandTableMap'
import SensorCards from './SensorCards'

export default function OperationsPage({
  snapshot,
  connected,
}: {
  snapshot: OperationsSnapshot | null
  connected: boolean
}) {
  return (
    <div className="space-y-4">
      <div className="ops-grid">
        <SandTableMap snapshot={snapshot} />
        <CameraColumn snapshot={snapshot} />
        <RadarScope snapshot={snapshot} />
      </div>
      <SensorCards snapshot={snapshot} />
      <div className="grid gap-4 lg:grid-cols-2">
        <ReasoningPanel snapshot={snapshot} />
        <EventLog snapshot={snapshot} />
      </div>
      <ControlBar snapshot={snapshot} connected={connected} />
      <LegacyPanel />
      {snapshot?.limitations?.length ? (
        <ul className="text-xs text-slate-500">
          {snapshot.limitations.map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : null}
    </div>
  )
}
