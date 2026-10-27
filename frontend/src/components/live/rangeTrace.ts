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

