import Panel from '../layout/Panel'
import type { OpenDialog } from '../../types/dialog'
import type { CameraCard, OperationsSnapshot } from '../../types/operations'
import { cameraShort, clockLabel, panelState } from './format'

const FALLBACK: CameraCard[] = [
  { camera_id: 'camera_top', name: 'Camera 1 · Top Overview', panoramic_360: false, state: 'disconnected', source_mode: 'unavailable', fps: null, width: null, height: null, last_frame_utc: null, error: 'Camera not opened.' },
  { camera_id: 'camera_ground_coordinate', name: 'Camera 2 · Ground Coordinate', panoramic_360: false, state: 'disconnected', source_mode: 'unavailable', fps: null, width: null, height: null, last_frame_utc: null, error: 'Camera not opened.' },
  { camera_id: 'camera_ground_inspection', name: 'Camera 3 · Ground Inspection', panoramic_360: false, state: 'disconnected', source_mode: 'unavailable', fps: null, width: null, height: null, last_frame_utc: null, error: 'Camera not opened.' },
]

export default function CameraCluster({
  snapshot,
  onOpen,
}: {
  snapshot: OperationsSnapshot | null
  onOpen: OpenDialog
}) {
  const cameras = snapshot?.cameras?.length ? snapshot.cameras : FALLBACK
  const online = snapshot?.streaming_camera_count ?? 0
  const total = snapshot?.camera_count ?? cameras.length
  const [primary, ...rest] = cameras

  return (
    <Panel
      className="camera-panel"
      testId="camera-panel"
      title={`Cameras · ${online}/${total} online`}
      state={online > 0 ? 'LIVE' : 'DISCONNECTED'}
      expandLabel="cameras"
      onExpand={() => onOpen({ kind: 'camera', cameraId: primary?.camera_id ?? 'camera_top' })}
    >
      <div className="camera-grid">
        {primary ? <Preview camera={primary} large onOpen={onOpen} /> : null}
        <div className="camera-row">
          {rest.map((camera) => <Preview key={camera.camera_id} camera={camera} onOpen={onOpen} />)}
        </div>
      </div>
    </Panel>
  )
}

function Preview({
  camera,
  large = false,
  onOpen,
}: {
  camera: CameraCard
  large?: boolean
  onOpen: OpenDialog
}) {
  const streaming = camera.state === 'connected' && camera.source_mode === 'live'
  return (
    <button
      type="button"
      className={`preview ${large ? 'preview-large' : ''}`}
      onClick={() => onOpen({ kind: 'camera', cameraId: camera.camera_id })}
    >
      <span className="preview-frame">
        <span className="preview-copy">{streaming ? 'Waiting for a stored frame' : 'No stream'}</span>
      </span>
      <span className="preview-label">
        {cameraShort(camera.camera_id)}
        <span>{panelState(camera.source_mode)} · {clockLabel(camera.last_frame_utc)}</span>
      </span>
    </button>
  )
}
