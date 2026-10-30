import { useEffect, useState } from 'react'
import type { OperationsSnapshot } from '../../types/operations'

function useSensorCountdown(snapshot: OperationsSnapshot | null): number {
  const until = snapshot?.sensor_countdown_until_ms ?? null
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!until) return
    const timer = window.setInterval(() => setNow(Date.now()), 200)
    return () => window.clearInterval(timer)
  }, [until])
  if (!until) return snapshot?.sensor_countdown_s ?? 0
  return Math.max(0, Math.ceil((until - now) / 1000))
}

export default function SensorCountdown({
  snapshot,
  sensor,
}: {
  snapshot: OperationsSnapshot | null
  sensor: string
}) {
  const seconds = useSensorCountdown(snapshot)
  if (seconds <= 0) return null
  return (
    <p className="quiet-line">
      Receiving {sensor} · {seconds}s
    </p>
  )
}
