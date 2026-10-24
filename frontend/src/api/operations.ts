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

export async function requestAdvisory(): Promise<void> {
  const response = await postJson('/api/ai/reason')
  if (!response.ok) throw new Error(await response.text())
}

export async function sendEstop(): Promise<void> {
  const response = await fetch('/api/mission/estop', { method: 'POST' })
  if (!response.ok) throw new Error(await response.text())
}

export async function clearOperationsView(): Promise<void> {
  const response = await postJson('/api/operations/clear')
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

export async function fetchGeometry(): Promise<unknown> {
  const response = await fetch('/api/config/geometry')
  if (!response.ok) throw new Error('geometry unavailable')
  return response.json()
}
