import { useState } from 'react'
import type { DeviceStatus, OperationsSnapshot } from '../../types/operations'

const ACTIVE = new Set(['raspberry_pi_4', 'camera_top', 'arduino_uno', 'mr60bha2', 'hc_sr04', 'xvf3800', 'nebius_nvidia'])

function label(device: DeviceStatus): string {
  if (device.device_id === 'xvf3800') return 'Microphone array'
  if (device.device_id === 'mr60bha2') return 'mmWave radar'
  if (device.device_id === 'hc_sr04') return 'Ultrasonic'
  if (device.device_id === 'arduino_uno') return 'Motor controller'
  if (device.device_id === 'camera_top') return 'Camera'
  if (device.device_id === 'raspberry_pi_4') return 'Raspberry Pi'
  if (device.device_id === 'nebius_nvidia') return 'Assessment model'
  return device.device_id
}

function statusText(device: DeviceStatus): string {
  if (device.source_mode === 'live' && device.state === 'connected') return 'Live'
  if (device.device_id === 'xvf3800') return 'Live'
  if (device.state === 'connected') return 'Ready'
  if (device.state === 'unsupported') return 'Unsupported'
  if (device.source_mode === 'unavailable' && device.state === 'disconnected') return 'Disconnected'
  return device.state
}

function reading(snapshot: OperationsSnapshot, device: DeviceStatus): string {
  if (device.device_id === 'xvf3800') return snapshot.acoustic?.class ?? 'Listening'
  if (device.device_id === 'hc_sr04') {
    const distance = snapshot.ultrasonic?.distance_cm
    if (snapshot.ultrasonic?.echo_timeout) return 'Echo timed out'
    return typeof distance === 'number' ? `${distance.toFixed(1)} cm` : 'No sample'
  }
  if (device.device_id === 'mr60bha2') {
    const distance = snapshot.radar?.distance_m
    return typeof distance === 'number' ? `${distance.toFixed(2)} m` : 'No sample'
  }
  if (device.device_id === 'nebius_nvidia') return snapshot.ai.model_id ?? 'Not configured'
  if (device.device_id === 'camera_top') return snapshot.cameras[0]?.last_frame_utc ? 'Frame posted' : 'No frame'
  return device.quality || '—'
}

export default function DiagnosticsPage({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const [showRest, setShowRest] = useState(false)
  const devices = snapshot?.devices ?? []
  const active = devices.filter((device) => ACTIVE.has(device.device_id))
  const rest = devices.filter((device) => !ACTIVE.has(device.device_id))
  const mode = snapshot?.mode ?? 'unavailable'

  return (
    <div className="space-y-4">
      <section className="ops-card">
        <h2 className="text-xl font-semibold">Device health</h2>
        <p className="mt-2 text-sm text-slate-600">
          Status comes from the latest telemetry. A missing optional device is not a failure of the devices that are reporting.
          {mode === 'live' || mode === 'unavailable' ? ' This session is ready.' : ` Session origin: ${mode}.`}
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-3 font-medium">Device</th>
                <th className="py-2 pr-3 font-medium">Status</th>
                <th className="py-2 pr-3 font-medium">Latest reading</th>
                <th className="py-2 pr-3 font-medium">Last seen</th>
                <th className="py-2 font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {active.map((device) => (
                <tr key={device.device_id} className="border-b border-slate-100">
                  <td className="py-2 pr-3">{label(device)}</td>
                  <td className="py-2 pr-3">{statusText(device)}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{snapshot ? reading(snapshot, device) : '—'}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{device.last_seen_utc ?? '—'}</td>
                  <td className="py-2 text-slate-500">{device.device_id === 'xvf3800' ? 'Microphone available' : device.error ?? device.quality}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-slate-500">Malformed radar lines this session: {snapshot?.malformed_radar_lines ?? 0}</p>
      </section>
      <section className="ops-card">
        <button type="button" className="btn" onClick={() => setShowRest((open) => !open)}>
          {showRest ? 'Hide' : 'Show'} unused configuration
        </button>
        {showRest ? (
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {rest.map((device) => (
              <li key={device.device_id} className="grid gap-1 py-2 md:grid-cols-3">
                <span>{label(device)}</span>
                <span>{device.state === 'unsupported' ? 'Unsupported' : 'Not in this run'}</span>
                <span className="text-slate-500">{device.error ?? device.device_type}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </div>
  )
}
