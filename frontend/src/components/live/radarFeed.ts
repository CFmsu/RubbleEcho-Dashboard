import type { OperationsSnapshot } from '../../types/operations'

export function radarRunning(snapshot: OperationsSnapshot | null): boolean {
  if (snapshot?.run_active) return true
  const radarMode = snapshot?.radar?.source_mode
  if (radarMode === 'live' || radarMode === 'simulation' || radarMode === 'replay') return true
  const device = snapshot?.devices?.find((item) => item.device_id === 'mr60bha2')
  return device?.source_mode === 'live' || device?.source_mode === 'simulation'
}
