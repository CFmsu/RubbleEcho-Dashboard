import RadarScope from '../operations/RadarScope'
import SensorCards from '../operations/SensorCards'
import type { OperationsSnapshot } from '../../types/operations'

export default function SensorsPage({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  return (
    <div className="space-y-4">
      <RadarScope snapshot={snapshot} />
      <SensorCards snapshot={snapshot} />
    </div>
  )
}
