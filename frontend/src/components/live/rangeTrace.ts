export interface RangeSample {
  t: number
  cm: number
}

const samples: RangeSample[] = []

export function noteRange(cm: number | null | undefined): RangeSample[] {
  if (cm == null || !Number.isFinite(cm)) return samples
  const now = Date.now()
  const last = samples[samples.length - 1]
  if (last && now - last.t < 420) return samples
  samples.push({ t: now, cm })
  if (samples.length > 80) samples.shift()
  return samples
}

export function readRange(): RangeSample[] {
  return samples
}

export function rangePath(values: RangeSample[], width: number, height: number): string {
  if (values.length === 0) return ''
  const max = Math.max(80, ...values.map((item) => item.cm))
  const step = width / Math.max(1, values.length - 1)
  return values
    .map((item, index) => {
      const x = index * step
      const y = height - (item.cm / max) * (height - 8) - 4
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
}

export function heartbeatPath(seconds: number, width: number, height: number): string {
  const steps = 84
  const beats = 3
  let path = ''
  for (let index = 0; index <= steps; index += 1) {
    const x = (index / steps) * width
    const local = (index / steps) * beats + seconds * 1.15
    const y = height * 0.58 - ecg(local % 1) * (height * 0.42)
    path += `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)} `
  }
  return path.trim()
}

function ecg(unit: number): number {
  if (unit < 0.12) return Math.sin((unit / 0.12) * Math.PI) * 0.16
  if (unit < 0.28) return 0
  if (unit < 0.34) return -Math.sin(((unit - 0.28) / 0.06) * Math.PI) * 0.2
  if (unit < 0.44) return Math.sin(((unit - 0.34) / 0.1) * Math.PI)
  if (unit < 0.52) return -Math.sin(((unit - 0.44) / 0.08) * Math.PI) * 0.28
  if (unit < 0.66) return 0
  if (unit < 0.86) return Math.sin(((unit - 0.66) / 0.2) * Math.PI) * 0.24
  return 0
}
