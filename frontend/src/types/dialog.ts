export type DialogRequest =
  | { kind: 'map'; pointId?: string }
  | { kind: 'camera'; cameraId: string }
  | { kind: 'radar' }
  | { kind: 'audio' }
  | { kind: 'vibration' }
  | { kind: 'ultrasonic' }
  | { kind: 'rover' }
  | { kind: 'evidence' }
  | { kind: 'events' }
  | { kind: 'diagnostics' }
  | { kind: 'export' }
  | { kind: 'knock' }
  | { kind: 'reset' }

export type OpenDialog = (request: DialogRequest) => void

export type ActionRunner = (action: () => Promise<string | void>) => Promise<string | void>
