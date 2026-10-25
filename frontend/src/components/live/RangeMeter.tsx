export default function RangeMeter({
  distanceM,
  presence,
  paused,
}: {
  distanceM: number | null | undefined
  presence: boolean | null | undefined
  paused: boolean
}) {
  const fraction = distanceM == null ? null : Math.max(0, Math.min(1, distanceM / 1.5))
  const label = paused
    ? 'No range sample'
    : presence
      ? 'Person reported in range'
      : 'No person reported'
  return (
    <div className="range-meter">
      <p>{label}</p>
      <div className="range-track">
        <span>0</span>
        {fraction != null ? <i className="range-mark" style={{ left: `${8 + fraction * 84}%` }} /> : null}
        <span>1.5 m</span>
      </div>
      <p>{distanceM == null ? 'Distance not reported' : `${distanceM} m along the beam`}</p>
    </div>
  )
}
