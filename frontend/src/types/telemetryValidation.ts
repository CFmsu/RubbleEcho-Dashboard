
import type { Telemetry } from './telemetry'

export function isValidTelemetry(data: unknown): data is Telemetry {
  if (typeof data !== 'object' || data === null) {
    return false
  }

  const t = data as Record<string, unknown>

  if (
    typeof t.robot !== 'object' ||
    t.robot === null ||
    typeof t.mission !== 'object' ||
    t.mission === null ||
    !Array.isArray(t.probes) ||
    !Array.isArray(t.events)
  ) {
    return false
  }

  const robot = t.robot as Record<string, unknown>
  const mission = t.mission as Record<string, unknown>

  const validNumber = (value: unknown): value is number =>
    typeof value === 'number' && Number.isFinite(value)

  const validConfidence = (value: unknown) =>
    validNumber(value) && value >= 0 && value <= 1

  const validPosition = (x: unknown, y: unknown) =>
    validNumber(x) && validNumber(y)

  const validStatuses = ['STANDBY', 'ACTIVE', 'PAUSED', 'DONE']
  const validPhases = ['explore', 'knock', 'listen', 'decide']
  const validScenarios = ['earthquake', 'flood', 'collapse']

  return (
    validPosition(robot.x, robot.y) &&
    validStatuses.includes(mission.status as string) &&
    validPhases.includes(mission.phase as string) &&
    validScenarios.includes(mission.scenario as string) &&
    typeof mission.probe_count === 'number' &&
    Number.isInteger(mission.probe_count) &&
    mission.probe_count >= 0 &&
    validConfidence(mission.confidence) &&
    t.probes.every((probe: unknown) => {
      if (typeof probe !== 'object' || probe === null) {
        return false
      }

      const p = probe as Record<string, unknown>

      return (
        typeof p.id === 'string' &&
        validPosition(p.x, p.y) &&
        validConfidence(p.confidence)
      )
    }) &&
    t.events.every(
      (event: unknown) => typeof event === 'string'
    )
  )
}
