import { motion, useReducedMotion } from 'framer-motion'

type Props = {
  samples: number[]
  label: string
  color?: string
  secondary?: number[]
  secondaryColor?: string
  large?: boolean
  instrument?: boolean
}

export default function SignalScope({
  samples,
  label,
  color = '#2563eb',
  secondary,
  secondaryColor = '#fdba74',
  large = false,
  instrument = false,
}: Props) {
  const reduce = useReducedMotion()
  const width = 100
  const height = large || instrument ? 36 : 16
  const waiting = samples.length < 2 && !(secondary && secondary.length > 1)
  const sweep = instrument && !reduce && !waiting
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={instrument ? 'signal-scope instrument' : large ? 'signal-scope large' : 'signal-scope'}
      role="img"
      aria-label={waiting ? `${label}, waiting for samples` : label}
    >
      <line x1="0" y1={height / 2} x2={width} y2={height / 2} className="scope-axis" />
      {large || instrument ? <Grid width={width} height={height} /> : null}
      {secondary && secondary.length > 1 ? <Trace values={secondary} width={width} height={height} color={secondaryColor} /> : null}
      {samples.length > 1 ? <Trace values={samples} width={width} height={height} color={color} /> : null}
      {sweep ? (
        <motion.line
          y1={1}
          y2={height - 1}
          stroke="rgba(37,99,235,0.45)"
          strokeWidth="0.35"
          initial={{ x1: 0, x2: 0 }}
          animate={{ x1: [0, width], x2: [0, width] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: 'linear' }}
        />
      ) : null}
    </svg>
  )
}

function Grid({ width, height }: { width: number; height: number }) {
  return (
    <g className="scope-grid">
      {[0.25, 0.5, 0.75].map((fraction) => (
        <line key={`y-${fraction}`} x1="0" y1={height * fraction} x2={width} y2={height * fraction} />
      ))}
      {[0.25, 0.5, 0.75].map((fraction) => (
        <line key={`x-${fraction}`} x1={width * fraction} y1="0" x2={width * fraction} y2={height} />
      ))}
    </g>
  )
}

function Trace({
  values,
  width,
  height,
  color,
}: {
  values: number[]
  width: number
  height: number
  color: string
}) {
  const peak = Math.max(1e-6, ...values.map((value) => Math.abs(value)))
  const step = width / Math.max(1, values.length - 1)
  const path = values
    .map((value, index) => {
      const x = index * step
      const y = height / 2 - (value / peak) * (height / 2 - 1.4)
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
  return <path d={path} fill="none" stroke={color} strokeWidth="0.7" strokeLinejoin="round" strokeLinecap="round" />
}
