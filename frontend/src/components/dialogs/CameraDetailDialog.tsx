import { useState } from 'react'
import { captureCamera } from '../../api/operations'
import type { ActionRunner } from '../../types/dialog'
import type { OperationsSnapshot } from '../../types/operations'
import { cameraShort, clockLabel, panelState } from '../live/format'
import DetailDialog, { FactGrid } from './DetailDialog'

export default function CameraDetailDialog({
  open,
  cameraId,
  snapshot,
  run,
  onClose,
}: {
  open: boolean
  cameraId: string
  snapshot: OperationsSnapshot | null
  run: ActionRunner
  onClose: () => void
}) {
  const camera = snapshot?.cameras.find((item) => item.camera_id === cameraId)
  const calibration = snapshot?.calibration
  const coordinate = cameraId === 'camera_ground_coordinate'
  const [result, setResult] = useState('')

  return (
    <DetailDialog open={open} onClose={onClose} title={camera?.name ?? cameraId} state={panelState(camera?.source_mode)}>
      <div className="preview preview-detail">
        <span className="preview-frame">
          {camera?.image_url ? (
            <img src={camera.image_url} alt="Camera frame" />
          ) : (
            <span className="preview-copy">{camera?.state === 'connected' ? 'No stored frame' : 'No stream'}</span>
          )}
        </span>
      </div>
      <FactGrid
        rows={[
          ['Label', cameraShort(cameraId)],
          ['State', camera?.state ?? 'disconnected'],
          ['Source', camera?.source_mode ?? 'live'],
          ['FPS', camera?.fps == null ? '—' : String(camera.fps)],
          ['Resolution', camera?.width && camera?.height ? `${camera.width}×${camera.height}` : '—'],
          ['Last frame', clockLabel(camera?.last_frame_utc)],
          ['Error', camera?.error ?? '—'],
          ['360° label', camera?.panoramic_360 ? 'verified' : 'not claimed'],
        ]}
      />
      {coordinate ? (
        <FactGrid
          rows={[
            ['ArUco markers', String(calibration?.marker_count ?? 0)],
            ['Homography', calibration?.homography_valid ? 'valid' : 'invalid'],
            ['RMS reprojection', calibration?.rms_px == null ? '—' : `${calibration.rms_px} px`],
            ['Pose', calibration?.pose_valid ? 'valid' : 'invalid'],
            ['Reason', calibration?.reason ?? 'no calibration'],
          ]}
        />
      ) : <p className="quiet-line">X/Y mapping is shown for the coordinate camera only after a valid transform.</p>}
      <button
        type="button"
        className="btn primary"
        disabled={camera?.state !== 'connected' && !camera?.image_url}
        onClick={() => {
          void run(async () => {
            await captureCamera(cameraId)
            return 'Capture requested.'
          }).then((message) => setResult(message ?? '')).catch((caught: unknown) => {
            setResult(caught instanceof Error ? caught.message : 'Capture failed')
          })
        }}
      >
        Capture frame
      </button>
      {result ? <p className="quiet-line" role="status">{result}</p> : null}
    </DetailDialog>
  )
}
