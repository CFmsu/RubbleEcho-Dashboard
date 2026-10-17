
import type { Scenario } from '../types/telemetry'

export type MissionAction =
  | 'demo'
  | 'start'
  | 'pause'
  | 'resume'
  | 'step'
  | 'reset'

export async function sendMissionCommand(
  action: MissionAction,
  scenario: Scenario
): Promise<void> {
  const response = await fetch(`/api/mission/${action}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ scenario }),
  })

  if (!response.ok) {
    throw new Error(`Mission command failed: ${action}`)
  }
}
