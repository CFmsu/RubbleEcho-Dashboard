import { motion, useReducedMotion } from 'framer-motion'

const MAX_CM = 100
const FACE = 36
const LANE_Y = 58
const TRACK = 250

export default function RangeLane({
  distanceCm,
  echoTimeout = false,
}: {
  distanceCm: number | null
  echoTimeout?: boolean
}) {
  const reduce = useReducedMotion()
  const heard = distanceCm != null && Number.isFinite(distanceCm) && !echoTimeout
  const clamped = heard ? Math.min(MAX_CM, Math.max(2, distanceCm)) : null
  const x = clamped == null ? FACE : FACE + (clamped / MAX_CM) * TRACK
  const stopX = FACE + (20 / MAX_CM) * TRACK
  const label = !heard
    ? echoTimeout
      ? 'Echo timed out'
      : 'No echo yet'
    : `${distanceCm} centimeters to the return`

  return (
    <svg className="range-lane" viewBox="0 0 320 116" role="img" aria-label={label}>
      <rect width="320" height="116" rx="8" fill="#f8fafc" />
      <rect x={FACE} y="28" width={stopX - FACE} height="60" fill="#f8efe3" />
      <text x={FACE + 4} y="80" fill="#b7791f" fontSize="8">20 cm</text>
      {[0, 25, 50, 75, 100].map((cm) => {
        const tick = FACE + (cm / MAX_CM) * TRACK
        return (
          <g key={cm}>
            <line x1={tick} y1="88" x2={tick} y2="94" stroke="#94a3b8" strokeWidth="1" />
            <text x={tick} y="106" fill="#5c6b80" fontSize="8" textAnchor="middle">{cm}</text>
          </g>
        )
      })}
      <line x1={FACE} y1={LANE_Y} x2={FACE + TRACK} y2={LANE_Y} stroke="#d5deea" strokeWidth="2" />
      <rect x="8" y="40" width="22" height="36" rx="3" fill="#1e293b" />
      <circle cx="28" cy="50" r="5" fill="#e2e8f0" stroke="#334155" strokeWidth="1" />
      <circle cx="28" cy="66" r="5" fill="#e2e8f0" stroke="#334155" strokeWidth="1" />
      {heard ? (
        <g>
          <line x1={FACE} y1={LANE_Y} x2={x} y2={LANE_Y} stroke="#2563eb" strokeWidth="2" />
          <motion.circle
            cy={LANE_Y}
            r="4"
            fill="#2563eb"
            initial={false}
            animate={reduce ? { cx: x } : { cx: [FACE, x, FACE] }}
            transition={reduce ? { duration: 0.2 } : { duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
          />
          <line x1={x} y1="34" x2={x} y2="82" stroke="#7c3aed" strokeWidth="1.4" />
          <circle cx={x} cy={LANE_Y} r="7" fill="#ddd6fe" stroke="#7c3aed" strokeWidth="1.4" />
          <text x={x} y="22" fill="#17243b" fontSize="11" textAnchor="middle">{distanceCm} cm</text>
        </g>
      ) : (
        <text x="160" y={LANE_Y + 4} fill="#5c6b80" fontSize="12" textAnchor="middle">
          {echoTimeout ? 'Echo timed out' : 'Waiting for an echo'}
        </text>
      )}
    </svg>
  )
}
