
export type MissionStatus =
  | 'STANDBY'
  | 'ACTIVE'
  | 'PAUSED'
  | 'DONE'

export type MissionPhase =
  | 'explore'
  | 'knock'
  | 'listen'
  | 'decide'

export type Scenario =
  | 'earthquake'
  | 'flood'
  | 'collapse'

export interface Mission {
  status: MissionStatus
  phase: MissionPhase
  scenario: Scenario
  probe_count: number
  confidence: number
}

export interface Robot {
  x: number
  y: number
}

export interface Probe {
  id: string
  x: number
  y: number
  confidence: number
}

export interface Telemetry {
  mission: Mission
  robot: Robot
  probes: Probe[]
  events: string[]
}
