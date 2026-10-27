import { motion, useReducedMotion } from 'framer-motion'
import { useId } from 'react'

const CX = 100
const CY = 108
const RING = 62
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

function figure(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return '—'
  return digits === 0 ? String(Math.round(value)) : value.toFixed(digits)
}

export default function RadarScope({
  distanceM,
  presence,
  targets,
  breath,
  heart,
  running,
}: {
  distanceM: number | null | undefined
  presence?: boolean | null
  targets?: number | null
  breath?: number | null
  heart?: number | null
  running: boolean
}) {
  const reduce = useReducedMotion()
  const still = !running || Boolean(reduce)
  const rawId = useId().replace(/:/g, '')
  const washId = `wash-${rawId}`
  const range = typeof distanceM === 'number' && distanceM > 0 ? Math.min(distanceM, MAX_M) : null
  const radius = range == null ? null : (range / MAX_M) * RING
  const blip = radius != null && presence === true ? point(0, radius) : null
  const ticks = Array.from({ length: 24 }, (_, index) => index * 15)

  return (
    <div className="ppi-frame" role="img" aria-label={caption(presence, range, breath, heart, targets)}>
      <svg className="ppi-scope" viewBox="0 0 200 216">
        <rect width="200" height="216" fill="#f7f9fc" />
        <Stat x={8} y={14} label="PRESENCE" value={presence == null ? '—' : presence ? 'YES' : 'NO'} hot={presence === true} />
        <Stat x={148} y={14} label="RANGE" value={range == null ? '—' : `${range.toFixed(2)} m`} hot={range != null} align="end" />
        <circle cx={CX} cy={CY} r={RING + 8} fill="#ffffff" stroke="#17243b" strokeWidth="1" />
        {[0.33, 0.66, 1].map((step) => (
          <circle key={step} cx={CX} cy={CY} r={RING * step} fill="none" stroke="#d5deea" strokeWidth={step === 1 ? 1 : 0.6} />
        ))}
        {radius != null ? (
          <circle cx={CX} cy={CY} r={radius} fill="none" stroke="#2563eb" strokeWidth="1.4" />
        ) : null}
        <line x1={CX} y1={CY - RING} x2={CX} y2={CY + RING} stroke="#d5deea" strokeWidth="0.5" />
        <line x1={CX - RING} y1={CY} x2={CX + RING} y2={CY} stroke="#d5deea" strokeWidth="0.5" />
        {ticks.map((bearing) => {
          const outer = point(bearing, RING)
          const inner = point(bearing, bearing % 90 === 0 ? RING - 5 : RING - 2.5)
          return <line key={bearing} x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} stroke="#17243b" strokeWidth={bearing % 90 === 0 ? 0.9 : 0.35} />
        })}
        {[0.5, 1, 1.5].map((meters) => {
          const mark = point(8, (meters / MAX_M) * RING)
          return (
            <text key={meters} x={mark.x + 3} y={mark.y + 2} fill="#64748b" fontSize="5.5">
              {meters.toFixed(1)}
            </text>
          )
        })}
        {blip ? (
          <g>
            <motion.circle
              cx={blip.x}
              cy={blip.y}
              r="5.5"
              fill="#2563eb"
              opacity="0.22"
              animate={still ? { opacity: 0.22 } : { opacity: [0.12, 0.4, 0.12] }}
              transition={still ? { duration: 0.2 } : { duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
            />
            <circle cx={blip.x} cy={blip.y} r="2.2" fill="#2563eb" stroke="#ffffff" strokeWidth="0.7" />
            <text x={blip.x + 4} y={blip.y - 4} fill="#17243b" fontSize="6">
              {range?.toFixed(2)} m
            </text>
          </g>
        ) : null}
        <circle cx={CX} cy={CY} r="1.3" fill="#17243b" />
        <Stat x={8} y={196} label="BREATH" value={breath == null ? '—' : `${figure(breath)} /min`} hot={breath != null && breath > 0.5} />
        <Stat x={192} y={196} label="HEART" value={heart == null ? '—' : `${figure(heart)} bpm`} hot={heart != null && heart > 0.5} align="end" />
      </svg>
      <motion.div
        className="ppi-sweep"
        animate={still ? { rotate: 0 } : { rotate: 360 }}
        transition={still ? { duration: 0.2 } : { duration: 2.4, repeat: Infinity, ease: 'linear' }}
      >
        <svg viewBox="0 0 200 216" aria-hidden="true">
          <defs>
            <linearGradient id={washId} x1={CX} y1={CY} x2={CX} y2={CY - RING} gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.05" />
              <stop offset="100%" stopColor="#2563eb" stopOpacity="0.55" />
            </linearGradient>
          </defs>
          <path d={sector(18)} fill="#2563eb" opacity="0.12" />
          <path d={sector(8)} fill={`url(#${washId})`} />
          <line x1={CX} y1={CY} x2={CX} y2={CY - RING} stroke="#2563eb" strokeWidth="1.1" />
        </svg>
      </motion.div>
    </div>
  )
}

function Stat({
  x,
  y,
  label,
  value,
  hot,
  align = 'start',
}: {
  x: number
  y: number
  label: string
  value: string
  hot: boolean
  align?: 'start' | 'end'
}) {
  const anchor = align === 'end' ? 'end' : 'start'
  return (
    <g>
      <text x={x} y={y} fill="#5c6b80" fontSize="6" textAnchor={anchor} letterSpacing="0.08em">{label}</text>
      <text x={x} y={y + 12} fill={hot ? '#17243b' : '#8b98a8'} fontSize="11" textAnchor={anchor}>{value}</text>
    </g>
  )
}

function caption(
  presence: boolean | null | undefined,
  range: number | null,
  breath: number | null | undefined,
  heart: number | null | undefined,
  targets: number | null | undefined,
): string {
  const who = presence == null ? 'presence unknown' : presence ? 'presence yes' : 'presence no'
  const where = range == null ? 'no range' : `${range.toFixed(2)} meters on the forward axis`
  const life = `${figure(breath)} breaths per minute, ${figure(heart)} beats per minute`
  const count = targets == null ? '' : `, ${targets} target${targets === 1 ? '' : 's'}`
  return `Radar ${who}, ${where}, ${life}${count}. Bearing is not reported.`
}
