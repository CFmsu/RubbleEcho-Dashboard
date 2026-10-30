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

export default function RadarScope({
  distanceM,
  presence,
  targets,
}: {
  distanceM: number | null | undefined
  presence?: boolean | null
  targets?: number | null
  running?: boolean
}) {
  const range = typeof distanceM === 'number' && distanceM > 0 ? Math.min(distanceM, MAX_M) : null
  const radius = range == null ? null : (range / MAX_M) * RING
  const ticks = Array.from({ length: 24 }, (_, index) => index * 15)

  return (
    <div className="ppi-frame" role="img" aria-label={caption(presence, range, targets)}>
      <svg className="ppi-scope" viewBox="0 0 200 216">
        <rect width="200" height="216" fill="#f7f9fc" />
        <Stat x={8} y={14} label="FLAG" value={presence == null ? '—' : presence ? 'SET' : 'CLEAR'} hot={false} />
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
        <circle cx={CX} cy={CY} r="1.3" fill="#17243b" />
      </svg>
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
  targets: number | null | undefined,
): string {
  const flag = presence == null ? 'presence flag not reported' : presence ? 'presence flag set' : 'presence flag clear'
  const where = range == null ? 'no range' : `${range.toFixed(2)} meters`
  const count = targets == null ? '' : `, ${targets} reported return${targets === 1 ? '' : 's'}`
  return `Radar ${flag}, ${where}${count}. This is not a confirmed person, and bearing is not reported.`
}
