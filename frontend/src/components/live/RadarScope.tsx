import { motion, useReducedMotion } from 'framer-motion'
import { useId } from 'react'

const CX = 100
const CY = 100
const RING = 72
const MAX_M = 1.5

function point(bearingDeg: number, radius: number): { x: number; y: number } {
  const radians = (bearingDeg * Math.PI) / 180
  return {
    x: CX + Math.sin(radians) * radius,
    y: CY - Math.cos(radians) * radius,
  }
}

function sector(halfDeg: number): string {
  const start = point(-halfDeg, RING)
  const end = point(halfDeg, RING)
  return `M ${CX} ${CY} L ${start.x} ${start.y} A ${RING} ${RING} 0 0 1 ${end.x} ${end.y} Z`
}

export default function RadarScope({
  distanceM,
  presence,
  targets,
  running,
}: {
  distanceM: number | null | undefined
  presence?: boolean | null
  targets?: number | null
  running: boolean
}) {
  const reduce = useReducedMotion()
  const still = !running || Boolean(reduce)
  const rawId = useId().replace(/:/g, '')
  const washId = `wash-${rawId}`
  const range = typeof distanceM === 'number' && distanceM > 0 ? Math.min(distanceM, MAX_M) : null
  const dots = detectionDots(range, presence, targets)
  const ticks = Array.from({ length: 36 }, (_, index) => index * 10)
  const labels = Array.from({ length: 12 }, (_, index) => index * 30)

  return (
    <div className="ppi-frame" role="img" aria-label="Radar scope">
      <svg className="ppi-scope" viewBox="0 0 200 200">
        <circle cx={CX} cy={CY} r="96" fill="#f7f9fc" stroke="#17243b" strokeWidth="1.1" />
        {[0.25, 0.5, 0.75, 1].map((step) => (
          <circle key={step} cx={CX} cy={CY} r={RING * step} fill="none" stroke="#d5deea" strokeWidth={step === 1 ? 1 : 0.7} />
        ))}
        {range != null ? (
          <circle cx={CX} cy={CY} r={(range / MAX_M) * RING} fill="none" stroke="#2563eb" strokeWidth="1.5" />
        ) : null}
        <line x1={CX} y1={CY - RING} x2={CX} y2={CY + RING} stroke="#d5deea" strokeWidth="0.5" />
        <line x1={CX - RING} y1={CY} x2={CX + RING} y2={CY} stroke="#d5deea" strokeWidth="0.5" />
        {ticks.map((bearing) => {
          const outer = point(bearing, RING)
          const inner = point(bearing, bearing % 30 === 0 ? RING - 6 : RING - 3)
          return (
            <line
              key={bearing}
              x1={inner.x}
              y1={inner.y}
              x2={outer.x}
              y2={outer.y}
              stroke="#17243b"
              strokeWidth={bearing % 30 === 0 ? 0.9 : 0.4}
            />
          )
        })}
        {labels.map((bearing) => {
          const label = point(bearing, 86)
          return (
            <text key={bearing} x={label.x} y={label.y} fill="#17243b" fontSize="6.5" textAnchor="middle" dominantBaseline="middle">
              {bearing}
            </text>
          )
        })}
        {[0.5, 1, 1.5].map((meters) => {
          const label = point(96, (meters / MAX_M) * RING)
          return (
            <text key={meters} x={label.x + 2} y={label.y - 1} fill="#64748b" fontSize="5.5" textAnchor="start">
              {Math.round(meters * 100)}
            </text>
          )
        })}
        {dots.map((dot) => (
          <circle key={`${dot.x}-${dot.y}`} cx={dot.x} cy={dot.y} r="2.4" fill="#2563eb" stroke="#ffffff" strokeWidth="0.7" />
        ))}
        <circle cx={CX} cy={CY} r="1.4" fill="#17243b" />
      </svg>
      <motion.div
        className="ppi-sweep"
        animate={still ? { rotate: 0 } : { rotate: 360 }}
        transition={still ? { duration: 0.2 } : { duration: 4.8, repeat: Infinity, ease: 'linear' }}
      >
        <svg viewBox="0 0 200 200" aria-hidden="true">
          <defs>
            <linearGradient id={washId} x1={CX} y1={CY} x2={CX} y2={CY - RING} gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#ffffff" stopOpacity="0.92" />
            </linearGradient>
          </defs>
          <path d={sector(26)} fill="#2563eb" opacity="0.12" />
          <path d={sector(14)} fill={`url(#${washId})`} />
          <line x1={CX} y1={CY} x2={CX} y2={CY - RING} stroke="#ffffff" strokeWidth="2.4" />
          <line x1={CX} y1={CY} x2={CX} y2={CY - RING} stroke="#2563eb" strokeWidth="0.8" />
        </svg>
      </motion.div>
    </div>
  )
}

function detectionDots(
  range: number | null,
  presence: boolean | null | undefined,
  targets: number | null | undefined,
): Array<{ x: number; y: number }> {
  if (range == null || presence !== true) return []
  const count = Math.max(1, Math.min(4, Math.round(targets ?? 1)))
  const radius = (range / MAX_M) * RING
  const step = 14
  const origin = -((count - 1) * step) / 2
  return Array.from({ length: count }, (_, index) => point(origin + index * step, radius))
}
