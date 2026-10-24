import { useState } from 'react'
import MissionControls from '../../components/MissionControls'
import MissionStatus from '../../components/MissionStatus'
import RoverMap from '../../components/RoverMap'
import { useTelemetry } from '../../hooks/useTelemetry'

export default function LegacyPanel({ startOpen = false }: { startOpen?: boolean }) {
  const [open, setOpen] = useState(startOpen)
  return (
    <section className="ops-card">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">Legacy 12×12 simulation</h2>
        <button type="button" className="rounded-lg border border-[#E1E7EF] px-3 py-2 text-sm" onClick={() => setOpen((value) => !value)}>
          {open ? 'Hide' : 'Show'}
        </button>
      </div>
      <p className="mt-2 text-sm text-slate-600">This grid is the original software demo. Its confidence values are simulated from a hidden coordinate and are not sand-table measurements.</p>
      {open ? <LegacyBody /> : null}
    </section>
  )
}

function LegacyBody() {
  const { telemetry, connectionStatus } = useTelemetry()
  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-2">
      <RoverMap robot={telemetry.robot} probes={telemetry.probes} />
      <MissionStatus confidence={telemetry.mission.confidence} phase={telemetry.mission.phase} events={telemetry.events} />
      <div className="lg:col-span-2">
        <MissionControls missionStatus={telemetry.mission.status} telemetryConnected={connectionStatus === 'connected'} />
      </div>
    </div>
  )
}
