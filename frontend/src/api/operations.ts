const TOKEN_KEY = 'rubbleecho.operatorToken'

export function readOperatorToken(): string {
  return sessionStorage.getItem(TOKEN_KEY) ?? ''
}

export function writeOperatorToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

function headers(): HeadersInit {
  const token = readOperatorToken()
  return token
    ? { 'Content-Type': 'application/json', 'X-Operator-Token': token }
    : { 'Content-Type': 'application/json' }
}

async function postJson(path: string, body?: unknown): Promise<Response> {
  return fetch(path, {
    method: 'POST',
    headers: headers(),
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export async function loadReplay(): Promise<string> {
  const response = await postJson('/api/trials/start', {
    mode: 'replay',
    fixture: 'sample_trial',
  })
  if (!response.ok) throw new Error(await response.text())
  const payload = (await response.json()) as { trial_id: string }
  return payload.trial_id
}

async function searchMessage(path: string): Promise<string> {
  const response = await fetch(path, { method: 'POST' })
  const payload = await response.json()
  if (!response.ok || payload.ok === false) throw new Error(payload.message ?? 'Search step failed')
  return payload.message as string
}

export function planGrid(): Promise<string> {
  return searchMessage('/api/search/plan')
}

export function guardObstacle(): Promise<string> {
  return searchMessage('/api/search/obstacle')
}

export function readSearchSignal(): Promise<string> {
  return searchMessage('/api/search/signal')
}

export async function requestAdvisory(): Promise<void> {
  const response = await postJson('/api/ai/reason')
  if (!response.ok) throw new Error(await response.text())
}

export async function startSimulation(): Promise<string> {
  const response = await fetch('/api/mission/run', { method: 'POST' })
  const text = await response.text()
  if (!response.ok) throw new Error(text || 'Run failed')
  return 'Scripted demo is running. It does not move the rover and it is not Raspberry Pi data.'
}

export async function startHardware(): Promise<string> {
  const response = await postJson('/api/mission/hardware', { authorize_motion: true })
  const text = await response.text()
  if (!response.ok) throw new Error(text || 'Rover start refused')
  const payload = JSON.parse(text) as { rover?: { sent?: boolean; port?: string | null } }
  if (payload.rover?.sent && payload.rover.port) {
    return `Rover start sent on ${payload.rover.port}. Waiting for Raspberry Pi samples.`
  }
  return 'Motion authorized. No rover port accepted the start. The dashboard is waiting for Raspberry Pi samples.'
}

export async function haltSimulation(): Promise<string> {
  const response = await fetch('/api/mission/halt', { method: 'POST' })
  const text = await response.text()
  if (!response.ok) throw new Error(text || 'Stop failed')
  const payload = JSON.parse(text) as { message?: string }
  return payload.message ?? 'Stopped.'
}

export async function sendEstop(): Promise<void> {
  const response = await fetch('/api/mission/estop', { method: 'POST' })
  if (!response.ok) throw new Error(await response.text())
}

export async function clearOperationsView(): Promise<void> {
  const response = await postJson('/api/operations/clear')
  if (!response.ok) throw new Error(await response.text())
}

export async function sendHold(): Promise<string> {
  const response = await fetch('/api/mission/stop', { method: 'POST' })
  if (!response.ok) throw new Error(await response.text())
  return 'Hold sent. Knock request disarmed. STOP drives Arduino pin A0 low when that port is open.'
}

export async function armSolenoid(consent: boolean): Promise<string> {
  const response = await fetch(`/api/operations/arm?consent=${consent ? 'true' : 'false'}`, {
    method: 'POST',
    headers: headers(),
  })
  const text = await response.text()
  if (!response.ok) throw new Error(text || 'Arm request failed')
  const payload = JSON.parse(text) as { accepted?: boolean; reason?: string }
  if (!payload.accepted) throw new Error(payload.reason ?? 'Arm refused')
  return 'Armed. A confirmed knock asks the Arduino to tap pin A0 three times.'
}

export async function requestKnock(): Promise<string> {
  const response = await postJson('/api/operations/knock', {
    width_ms: 200,
    consent: true,
    rover_moving: false,
    now_ms: Date.now(),
    arm_first: false,
  })
  const text = await response.text()
  if (!response.ok) throw new Error(text || 'Knock request failed')
  const payload = JSON.parse(text) as {
    accepted?: boolean
    reason?: string
    link?: { sent?: boolean; port?: string | null }
  }
  if (!payload.accepted) throw new Error(payload.reason ?? 'Knock refused')
  if (payload.link?.sent) {
    return `Knock sent to ${payload.link.port}. Pin A0 taps three times, 200 ms on and 200 ms off.`
  }
  return 'Knock accepted. No Arduino port is open, so pin A0 was not driven.'
}

export async function captureCamera(cameraId: string): Promise<void> {
  const response = await postJson(`/api/camera/${cameraId}/capture`)
  if (!response.ok) throw new Error(await response.text())
}

export async function downloadExport(trialId: string, format: 'zip' | 'json' | 'csv'): Promise<void> {
  const response = await fetch(`/api/trials/${trialId}/export?format=${format}`, {
    headers: headers(),
  })
  if (!response.ok) throw new Error(await response.text())
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${trialId}.${format}`
  link.click()
  URL.revokeObjectURL(url)
}

export async function listenMicrophone(): Promise<string> {
  const response = await fetch('/api/audio/listen', { method: 'POST' })
  const payload = await response.json()
  if (!response.ok || payload.ok === false) {
    const detail = payload.detail ?? payload
    throw new Error(detail.message ?? 'Microphone did not open')
  }
  return payload.message as string
}

export async function startDummyRadar(): Promise<string> {
  const response = await fetch('/api/radar/dummy', { method: 'POST' })
  const payload = await response.json()
  if (!response.ok || payload.ok === false) throw new Error(payload.message ?? 'Dummy radar did not start')
  return payload.message as string
}

export async function startPiMimic(): Promise<string> {
  const response = await fetch('/api/radar/pi-mimic', { method: 'POST' })
  const payload = await response.json()
  if (!response.ok || payload.ok === false) throw new Error(payload.message ?? 'Pi mimic did not start')
  return payload.message as string
}

export async function listenRadar(): Promise<string> {
  const response = await fetch('/api/radar/listen', { method: 'POST' })
  const payload = await response.json()
  if (!response.ok || payload.ok === false) {
    const detail = payload.detail ?? payload
    throw new Error(detail.message ?? 'Radar did not open')
  }
  return payload.message as string
}

export async function stopRadar(): Promise<string> {
  const response = await fetch('/api/radar/stop', { method: 'POST' })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.message ?? 'Radar stop failed')
  return payload.message as string
}

export async function stopMicrophone(): Promise<string> {
  const response = await fetch('/api/audio/stop', { method: 'POST' })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.message ?? 'Microphone stop failed')
  return payload.message as string
}

export async function fetchGeometry(): Promise<unknown> {
  const response = await fetch('/api/config/geometry')
  if (!response.ok) throw new Error('geometry unavailable')
  return response.json()
}
