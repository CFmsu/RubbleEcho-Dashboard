import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { CameraCard, OperationsSnapshot } from '../../types/operations'
import { clockLabel, panelState } from './format'

const FALLBACK: CameraCard = {
  camera_id: 'camera_top',
  name: 'Camera',
  panoramic_360: false,
  state: 'disconnected',
  source_mode: 'unavailable',
  fps: null,
  width: null,
  height: null,
  last_frame_utc: null,
  error: 'Camera not opened.',
}

export default function CameraCluster({
  snapshot,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  onOpen: OpenDialog
}) {
  const camera = snapshot?.cameras?.find((item) => item.camera_id === 'camera_top') ?? snapshot?.cameras?.[0] ?? FALLBACK
  const live = camera.state === 'connected' && camera.source_mode === 'live'
  const sample = Boolean(camera.image_url)
  const title = live ? 'Camera · 1/1 online' : sample ? 'Camera · frame' : 'Camera · 0/1 online'
  const state = live ? 'LIVE' : sample ? 'FRAME' : 'DISCONNECTED'

  return (
    <Panel
      className="camera-panel"
      testId="camera-panel"
      title={title}
      state={state}
      expandLabel="camera"
      onExpand={() => onOpen({ kind: 'camera', cameraId: camera.camera_id })}
    >
      <div className="camera-grid is-single">
        <button
          type="button"
          className="preview preview-large"
          onClick={() => onOpen({ kind: 'camera', cameraId: camera.camera_id })}
        >
          <span className="preview-frame">
            {camera.image_url ? (
              <img src={camera.image_url} alt="Simulation camera sample" />
            ) : (
              <span className="preview-copy">{live ? 'Waiting for a stored frame' : 'No stream'}</span>
            )}
          </span>
          <span className="preview-label">
            Camera
            <span>{panelState(camera.source_mode)} · {clockLabel(camera.last_frame_utc)}</span>
          </span>
        </button>
      </div>
    </Panel>
  )
}
