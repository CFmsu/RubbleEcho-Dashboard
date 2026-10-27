import { useCallback, useEffect, useState } from 'react'
import {
  captureCamera,
  clearOperationsView,
  haltSimulation,
  guardObstacle,
  listenMicrophone,
  listenRadar,
  loadReplay,
  planGrid,
  readOperatorToken,
  readSearchSignal,
  stopMicrophone,
  requestKnock,
  sendHold,
  startDummyRadar,
  startPiMimic,
  startSimulation,
  stopRadar,
} from '../api/operations'
import AudioDetailDialog from '../components/dialogs/AudioDetailDialog'
import CameraDetailDialog from '../components/dialogs/CameraDetailDialog'
import DetailDialog from '../components/dialogs/DetailDialog'
import DiagnosticsDialog from '../components/dialogs/DiagnosticsDialog'
import EvidenceDetailDialog from '../components/dialogs/EvidenceDetailDialog'
import EventLogDialog from '../components/dialogs/EventLogDialog'
import MapDetailDialog from '../components/dialogs/MapDetailDialog'
import RadarDetailDialog from '../components/dialogs/RadarDetailDialog'
import RoverDetailDialog from '../components/dialogs/RoverDetailDialog'
import TrialExportDialog from '../components/dialogs/TrialExportDialog'
import UltrasonicDetailDialog from '../components/dialogs/UltrasonicDetailDialog'
import VibrationDetailDialog from '../components/dialogs/VibrationDetailDialog'
import MissionToolbar from '../components/layout/MissionToolbar'
import CameraCluster from '../components/live/CameraCluster'
import { APP_VERSION, footerMode, snapshotAge } from '../components/live/format'
import OperatorControls from '../components/live/OperatorControls'
import RadarOverview from '../components/live/RadarOverview'
import SignalWall from '../components/live/SignalWall'
import TestbedOverview from '../components/live/TestbedOverview'
import { useGeometry } from '../hooks/useGeometry'
import type { ActionRunner, DialogRequest } from '../types/dialog'
import type { OperationsSnapshot } from '../types/operations'

export default function LiveOperations({
  snapshot,
  connected,
}: {
  snapshot: OperationsSnapshot | null
  connected: boolean
}) {
  const { geometry, error } = useGeometry()
  const [active, setActive] = useState<DialogRequest | null>(null)
  const [showBoxes, setShowBoxes] = useState(false)
  const [hasToken, setHasToken] = useState(() => readOperatorToken().length > 0)
  const [notice, setNotice] = useState('')
  const [actionError, setActionError] = useState('')
  const close = useCallback(() => setActive(null), [])
  const run = useCallback<ActionRunner>(async (action) => {
    setActionError('')
    setNotice('')
    try {
      const message = await action()
      setNotice(message ?? '')
      return message
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : 'Request failed'
      setActionError(message)
      throw caught
    }
  }, [])

  return (
    <>
      <MissionToolbar
        snapshot={snapshot}
        hasToken={hasToken}
        status={actionError || notice}
        onOpen={setActive}
        onRun={() => void run(() => startSimulation())}
        onStop={() => void run(() => haltSimulation())}
        onCapture={() => {
          const cameras = (snapshot?.cameras ?? []).filter((camera) => camera.state === 'connected')
          void run(async () => {
            for (const camera of cameras) await captureCamera(camera.camera_id)
            return cameras.length ? 'Capture requested.' : 'No camera is open.'
          })
        }}
      />
      <div className="live-main" data-testid="live-main">
        <OperatorControls
          compact
          snapshot={snapshot}
          connected={connected}
          hasToken={hasToken}
          notice={notice}
          error={actionError}
          onOpen={setActive}
          onHold={() => void run(() => sendHold())}
          onReplay={() => void run(async () => {
            const trialId = await loadReplay()
            return `Replay ${trialId} loaded. It is not live hardware.`
          })}
          onListen={() => void run(async () => {
            const listening = snapshot?.devices?.some((device) => device.device_id === 'xvf3800' && device.source_mode === 'live')
            return listening ? stopMicrophone() : listenMicrophone()
          })}
          onRadarDummy={() => void run(async () => (
            snapshot?.radar?.case_name === 'dummy_mr60bha2' ? stopRadar() : startDummyRadar()
          ))}
          onPiMimic={() => void run(async () => (
            snapshot?.radar?.case_name === 'Pi mimic' ? stopRadar() : startPiMimic()
          ))}
          onRadarLive={() => void run(async () => {
            const live = snapshot?.devices?.some((device) => device.device_id === 'mr60bha2' && device.source_mode === 'live')
            return live ? stopRadar() : listenRadar()
          })}
          onPlan={() => void run(() => planGrid())}
          onObstacle={() => void run(() => guardObstacle())}
          onSignal={() => void run(() => readSearchSignal())}
        />
        <div className="live-primary" data-testid="live-primary">
          <TestbedOverview snapshot={snapshot} geometry={geometry} error={error} showBoxes={showBoxes} onOpen={setActive} />
          <CameraCluster snapshot={snapshot} onOpen={setActive} />
          <RadarOverview snapshot={snapshot} onOpen={setActive} />
        </div>
        <div className="live-secondary">
          <SignalWall snapshot={snapshot} onOpen={setActive} />
        </div>
      </div>
      <footer className="app-footer">
        <span>v{APP_VERSION}</span>
        <span>{footerMode(snapshot)}</span>
        <FooterAge snapshot={snapshot} />
        <span>trial {snapshot?.trial_id ?? '—'}</span>
      </footer>
      {active?.kind === 'map' ? (
        <MapDetailDialog
          key={active.pointId ?? 'map'}
          open
          pointId={active.pointId}
          snapshot={snapshot}
          geometry={geometry}
          showBoxes={showBoxes}
          onShowBoxes={setShowBoxes}
          onClose={close}
        />
      ) : null}
      {active?.kind === 'camera' ? (
        <CameraDetailDialog open cameraId={active.cameraId} snapshot={snapshot} run={run} onClose={close} />
      ) : null}
      {active?.kind === 'radar' ? <RadarDetailDialog open snapshot={snapshot} onClose={close} /> : null}
      {active?.kind === 'audio' ? <AudioDetailDialog open snapshot={snapshot} onClose={close} /> : null}
      {active?.kind === 'vibration' ? <VibrationDetailDialog open snapshot={snapshot} onClose={close} /> : null}
      {active?.kind === 'ultrasonic' ? <UltrasonicDetailDialog open snapshot={snapshot} onClose={close} /> : null}
      {active?.kind === 'rover' ? (
        <RoverDetailDialog open snapshot={snapshot} hasToken={hasToken} run={run} onClose={close} />
      ) : null}
      {active?.kind === 'evidence' ? <EvidenceDetailDialog open snapshot={snapshot} run={run} onClose={close} /> : null}
      {active?.kind === 'events' ? <EventLogDialog open snapshot={snapshot} onClose={close} /> : null}
      {active?.kind === 'diagnostics' ? (
        <DiagnosticsDialog open snapshot={snapshot} onToken={(token) => setHasToken(token.length > 0)} onClose={close} />
      ) : null}
      {active?.kind === 'export' ? <TrialExportDialog open snapshot={snapshot} run={run} onClose={close} /> : null}
      {active?.kind === 'knock' ? (
        <DetailDialog open title="Knock test" state={snapshot?.solenoid.state ?? 'DISARMED'} onClose={close} dismissOnBackdrop={false}>
          <p>This sends KNOCK to the Arduino solenoid sketch. Pin A0 taps three times: 200 ms on, 200 ms off. Stop drives the pin low.</p>
          <div className="button-row">
            <button type="button" className="btn" onClick={close}>Cancel</button>
            <button
              type="button"
              className="btn primary"
              onClick={() => void run(async () => {
                const message = await requestKnock()
                close()
                return message
              })}
            >
              Confirm request
            </button>
          </div>
        </DetailDialog>
      ) : null}
      {active?.kind === 'reset' ? (
        <DetailDialog open title="Reset view" onClose={close} dismissOnBackdrop={false}>
          <p>Clear the on-screen trial? Files already downloaded are kept.</p>
          <div className="button-row">
            <button type="button" className="btn" onClick={close}>Cancel</button>
            <button
              type="button"
              className="btn primary"
              onClick={() => void run(async () => {
                await clearOperationsView()
                close()
                return 'View cleared. Stored exports were not deleted.'
              })}
            >
              Clear view
            </button>
          </div>
        </DetailDialog>
      ) : null}
    </>
  )
}

function FooterAge({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  const [, setTick] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setTick((value) => value + 1), 1000)
    return () => window.clearInterval(id)
  }, [])
  return <span>{snapshotAge(snapshot)}</span>
}
