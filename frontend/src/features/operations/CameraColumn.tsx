import type { OperationsSnapshot } from '../../types/operations'

export default function CameraColumn({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const cameras = snapshot?.cameras ?? []
  const calibration = snapshot?.calibration
  return (
    <section className="ops-card">
      <h2 className="text-xl font-semibold">Cameras</h2>
      <p className="mt-1 text-xs text-slate-500">
        Streaming {snapshot?.streaming_camera_count ?? 0}/{snapshot?.camera_count ?? 1}. A card stays disconnected until a frame is actually captured.
      </p>
      <div className="mt-3 grid gap-3">
        {cameras.map((camera) => (
          <article key={camera.camera_id} className="rounded-lg border border-[#E1E7EF] p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <h3 className="font-medium">{camera.name}</h3>
              <span className="rounded bg-slate-200 px-2 py-0.5 text-xs">{camera.state.toUpperCase()}</span>
            </div>
            <div className="flex h-28 items-center justify-center rounded-lg bg-slate-100 text-sm text-slate-600">
              {camera.state === 'connected' ? 'Waiting for a stored frame' : 'DISCONNECTED'}
            </div>
            <p className="mt-2 text-xs text-slate-500">
              FPS {camera.fps ?? '—'} · {camera.width ?? '—'}×{camera.height ?? '—'} · age — · source {camera.source_mode}
            </p>
            <p className="text-xs text-slate-500">{camera.error ?? 'No error recorded.'} {camera.panoramic_360 ? '' : 'Not labeled 360°.'}</p>
          </article>
        ))}
        {cameras.length === 0 ? <p className="text-sm">Camera status has not arrived.</p> : null}
      </div>
      <p className="mt-3 text-xs">
        ArUco markers {calibration?.marker_count ?? 0} · homography {calibration?.homography_valid ? 'valid' : 'invalid'} · RMS {calibration?.rms_px ?? '—'} px · {calibration?.reason ?? 'no calibration'}
      </p>
    </section>
  )
}
