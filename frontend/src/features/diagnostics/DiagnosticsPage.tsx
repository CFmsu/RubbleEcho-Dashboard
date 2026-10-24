import { Architecture } from '../../pages/Architecture'
import type { OperationsSnapshot } from '../../types/operations'

export default function DiagnosticsPage({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  return (
    <div className="space-y-4">
      <section className="ops-card">
        <h2 className="text-xl font-semibold">Device health</h2>
        <p className="mt-2 text-sm text-slate-600">A row is connected only after a sample or a verified live call. Rendering this table does not mark hardware online.</p>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {(snapshot?.devices ?? []).map((device) => (
            <li key={device.device_id} className="grid gap-1 py-2 md:grid-cols-4">
              <span className="font-medium">{device.device_id}</span>
              <span>{device.state}</span>
              <span>{device.source_mode}</span>
              <span className="text-slate-500">{device.error ?? device.quality}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-slate-500">Malformed radar lines this session: {snapshot?.malformed_radar_lines ?? 0}</p>
      </section>
      <Architecture />
    </div>
  )
}
