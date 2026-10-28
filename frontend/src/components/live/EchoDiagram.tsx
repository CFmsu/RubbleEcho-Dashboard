import { useEffect, useMemo, useRef, useState } from 'react'

type Point = { x: number; y: number }

export default function EchoDiagram({
  distanceCm,
  echoTimeout = false,
  compact = false,
}: {
  distanceCm: number | null
  echoTimeout?: boolean
  compact?: boolean
}) {
  const heard = distanceCm != null && Number.isFinite(distanceCm) && !echoTimeout
  const shown = useShownDistance(heard ? distanceCm : null)
  const span = beamSpan(shown, heard)
  const scene = useMemo(
    () => (compact ? compactScene(span, heard) : fullScene(span, heard)),
    [compact, span, heard],
  )
  const outRef = useRef<SVGCircleElement>(null)
  const backRef = useRef<SVGCircleElement>(null)

  useEffect(() => {
    const outbound = outRef.current
    const inbound = backRef.current
    if (!outbound || !inbound) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!heard || reduced) {
      place(outbound, scene.out[0], 0)
      place(inbound, scene.back[0], 0)
      return
    }
    let frame = 0
    const started = performance.now()
    const loop = (now: number) => {
      const phase = ((now - started) % 1600) / 1600
      if (phase < 0.5) {
        place(outbound, bezier(scene.out[0], scene.out[1], scene.out[2], phase / 0.5), 1)
        place(inbound, scene.back[2], 0)
      } else {
        place(outbound, scene.out[2], 0)
        place(inbound, bezier(scene.back[0], scene.back[1], scene.back[2], (phase - 0.5) / 0.5), 1)
      }
      frame = requestAnimationFrame(loop)
    }
    frame = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(frame)
  }, [heard, scene])

  const label = !heard
    ? echoTimeout
      ? 'Ultrasonic echo timed out before it returned'
      : 'Ultrasonic sensor waiting for an echo'
    : `Ultrasonic time of flight, ${distanceCm} centimeters to the object in front`

  return (
    <svg
      viewBox={compact ? '0 0 148 40' : '0 0 680 292'}
      className={compact ? 'echo-sketch' : 'echo-figure'}
      role="img"
      aria-label={label}
    >
      {compact ? <CompactBody scene={scene} heard={heard} /> : <FullBody scene={scene} heard={heard} distanceCm={heard ? distanceCm : null} echoTimeout={echoTimeout} />}
      {scene.rays.map((ray) => (
        <path key={ray.id} d={curve(ray.from, ray.control, ray.to)} className={ray.back ? 'echo-ray is-back' : 'echo-ray is-out'} />
      ))}
      <circle ref={outRef} r={compact ? 1.7 : 4.2} fill="#2563eb" opacity="0" />
      <circle ref={backRef} r={compact ? 1.7 : 4.2} fill="#2563eb" opacity="0" />
    </svg>
  )
}

type Scene = ReturnType<typeof fullScene>

function CompactBody({ scene, heard }: { scene: Scene; heard: boolean }) {
  return (
    <g>
      <rect x="3" y="6" width="8" height="28" rx="1.5" fill="#166534" />
      <Transducers x={16} top={11} bottom={29} scale={0.42} />
      {heard ? <circle cx={scene.object.x} cy={scene.object.y} r={scene.object.r} fill="#ddd6fe" stroke="#7c3aed" strokeWidth="1" /> : null}
    </g>
  )
}

function FullBody({
  scene,
  heard,
  distanceCm,
  echoTimeout,
}: {
  scene: Scene
  heard: boolean
  distanceCm: number | null
  echoTimeout: boolean
}) {
  const face = 228
  const objectEdge = scene.object.x - scene.object.r
  return (
    <g>
      <text x="18" y="28" fill="#334155" fontSize="15">Microcontroller</text>
      <rect x="28" y="42" width="78" height="108" rx="4" fill="#166534" />
      <rect x="38" y="56" width="58" height="8" fill="#fbbf24" />
      <rect x="38" y="72" width="58" height="8" fill="#fbbf24" />
      <rect x="38" y="88" width="40" height="8" fill="#86efac" />
      <rect x="38" y="112" width="58" height="22" rx="2" fill="#14532d" />
      <path d="M106 78 H150 V92" fill="none" stroke="#334155" strokeWidth="1.4" />
      <path d="M106 118 H150 V150" fill="none" stroke="#334155" strokeWidth="1.4" />
      <g transform="translate(46 168)">
        <path d="M8 0 H32 L20 16 L32 32 H8 L20 16 Z" fill="none" stroke="#334155" strokeWidth="1.5" />
        <path d="M12 6 H28 L20 16 Z" fill="#b45309" />
      </g>
      <text x="18" y="222" fill="#334155" fontSize="14">Time of flight</text>

      <text x="168" y="28" fill="#334155" fontSize="15">Ultrasonic sensor</text>
      <rect x="168" y="58" width="28" height="128" rx="3" fill="#1e293b" />
      <Transducers x={196} top={86} bottom={150} scale={1} />

      {heard ? (
        <g>
          <circle cx={scene.object.x} cy={scene.object.y} r={scene.object.r} fill="#ddd6fe" stroke="#7c3aed" strokeWidth="2" />
          <text x={scene.object.x} y={scene.object.y - scene.object.r - 10} textAnchor="middle" fill="#334155" fontSize="14">Detected object</text>
          <line x1={face} y1="252" x2={objectEdge} y2="252" stroke="#17243b" strokeWidth="1.4" />
          <line x1={face} y1="244" x2={face} y2="260" stroke="#17243b" strokeWidth="1.4" />
          <line x1={objectEdge} y1="244" x2={objectEdge} y2="260" stroke="#17243b" strokeWidth="1.4" />
          <text x={(face + objectEdge) / 2} y="278" textAnchor="middle" fill="#17243b" fontSize="14">
            Measured distance {distanceCm} cm
          </text>
        </g>
      ) : (
        <text x="430" y="140" fill="#5c6b80" fontSize="15">{echoTimeout ? 'Echo timed out' : 'No echo yet'}</text>
      )}
    </g>
  )
}

function Transducers({ x, top, bottom, scale }: { x: number; top: number; bottom: number; scale: number }) {
  const w = 16 * scale
  const h = 18 * scale
  const r = 9 * scale
  return (
    <g>
      <Can x={x} y={top} w={w} h={h} r={r} />
      <Can x={x} y={bottom} w={w} h={h} r={r} />
    </g>
  )
}

function Can({ x, y, w, h, r }: { x: number; y: number; w: number; h: number; r: number }) {
  return (
    <g>
      <rect x={x} y={y - h / 2} width={w} height={h} rx={2} fill="#64748b" />
      <circle cx={x + w + r * 0.15} cy={y} r={r} fill="#e2e8f0" stroke="#334155" strokeWidth={Math.max(1, r * 0.12)} />
      <circle cx={x + w + r * 0.15} cy={y} r={r * 0.42} fill="#94a3b8" />
    </g>
  )
}

function beamSpan(distanceCm: number | null, heard: boolean): number {
  if (!heard || distanceCm == null) return 0.72
  const cm = Math.min(100, Math.max(2, distanceCm))
  return (cm - 2) / 98
}

function useShownDistance(distanceCm: number | null): number | null {
  const [shown, setShown] = useState<number | null>(distanceCm)
  const shownRef = useRef(distanceCm)
  useEffect(() => {
    if (distanceCm == null) {
      shownRef.current = null
      const frame = requestAnimationFrame(() => setShown(null))
      return () => cancelAnimationFrame(frame)
    }
    const from = shownRef.current ?? distanceCm
    const to = distanceCm
    if (Math.abs(from - to) < 0.05 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      shownRef.current = to
      const frame = requestAnimationFrame(() => setShown(to))
      return () => cancelAnimationFrame(frame)
    }
    const started = performance.now()
    let frame = 0
    const loop = (now: number) => {
      const t = Math.min(1, (now - started) / 480)
      const value = from + (to - from) * (1 - (1 - t) ** 3)
      shownRef.current = value
      setShown(value)
      if (t < 1) frame = requestAnimationFrame(loop)
    }
    frame = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(frame)
  }, [distanceCm])
  return shown
}

function fullScene(span: number, heard: boolean) {
  const object = { x: 248 + span * 390, y: 128, r: 28 }
  const face = { x: object.x - object.r + 2, y: object.y }
  const tx = { x: 224, y: 86 }
  const rx = { x: 224, y: 150 }
  return {
    object,
    out: [tx, { x: (tx.x + face.x) / 2, y: tx.y - 36 }, { x: face.x, y: face.y - 8 }] as [Point, Point, Point],
    back: [{ x: face.x, y: face.y + 8 }, { x: (rx.x + face.x) / 2, y: rx.y + 36 }, rx] as [Point, Point, Point],
    rays: heard ? rays(tx, rx, face, 22) : [],
  }
}

function compactScene(span: number, heard: boolean) {
  const object = { x: 36 + span * 100, y: 20, r: 6.5 }
  const face = { x: object.x - object.r, y: object.y }
  const tx = { x: 28, y: 11 }
  const rx = { x: 28, y: 29 }
  return {
    object,
    out: [tx, { x: (tx.x + face.x) / 2, y: 4 }, { x: face.x, y: face.y - 2 }] as [Point, Point, Point],
    back: [{ x: face.x, y: face.y + 2 }, { x: (rx.x + face.x) / 2, y: 36 }, rx] as [Point, Point, Point],
    rays: heard ? rays(tx, rx, face, 5) : [],
  }
}

function rays(tx: Point, rx: Point, face: Point, spread: number) {
  return [-1, 0, 1].flatMap((step) => {
    const outTo = { x: face.x, y: face.y - 6 + step * 3 }
    const backFrom = { x: face.x, y: face.y + 6 + step * 3 }
    return [
      {
        id: `out-${step}`,
        back: false,
        from: tx,
        control: { x: (tx.x + outTo.x) / 2, y: tx.y - spread + step * spread * 0.35 },
        to: outTo,
      },
      {
        id: `back-${step}`,
        back: true,
        from: backFrom,
        control: { x: (rx.x + backFrom.x) / 2, y: rx.y + spread + step * spread * 0.35 },
        to: rx,
      },
    ]
  })
}

function curve(from: Point, control: Point, to: Point): string {
  return `M ${from.x} ${from.y} Q ${control.x} ${control.y} ${to.x} ${to.y}`
}

function bezier(p0: Point, p1: Point, p2: Point, t: number): Point {
  const u = 1 - t
  return {
    x: u * u * p0.x + 2 * u * t * p1.x + t * t * p2.x,
    y: u * u * p0.y + 2 * u * t * p1.y + t * t * p2.y,
  }
}

function place(node: SVGCircleElement, point: Point, opacity: number) {
  node.setAttribute('cx', point.x.toFixed(1))
  node.setAttribute('cy', point.y.toFixed(1))
  node.setAttribute('opacity', String(opacity))
}
