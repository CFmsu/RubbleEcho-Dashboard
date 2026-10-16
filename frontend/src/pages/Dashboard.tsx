import { useState } from "react";
import { CameraPanel } from "../components/sensors/CameraPanel";
import { ComparisonPanel } from "../components/mission/ComparisonPanel";
import { ConfidenceGauge } from "../components/mission/ConfidenceGauge";
import { DetailTile } from "../components/common/DetailTile";
import { EventLog } from "../components/mission/EventLog";
import { FusionPanel } from "../components/sensors/FusionPanel";
import { MissionControls } from "../components/mission/MissionControls";
import { Panel } from "../components/common/Panel";
import { PopOut } from "../components/common/PopOut";
import { ProbeTimeline } from "../components/mission/ProbeTimeline";
import { SearchMap } from "../components/map/SearchMap";
import { SummaryCards } from "../components/mission/SummaryCards";
import { TypewriterNarrator } from "../components/mission/TypewriterNarrator";
import { WaveformChart } from "../components/sensors/WaveformChart";
import { RangePanel } from "../components/sensors/RangePanel";
import type { ScenarioPreset, TelemetrySnapshot } from "../types/mission";
import { demoNarrationBeat } from "../utils/demoNarration";
import { formatPercent } from "../utils/format";

type DetailId = "camera" | "knock" | "listen" | "score" | "log" | "compare" | "why" | null;

export function Dashboard({
  snapshot,
  scenarios,
  presentation,
  busy,
  onScenario,
  onStrategy,
  onDemo,
  onStart,
  onPause,
  onResume,
  onReset,
  onStep,
  onSpeed,
}: {
  snapshot: TelemetrySnapshot | null;
  scenarios: ScenarioPreset[];
  presentation: boolean;
  busy: boolean;
  onScenario: (id: string) => void;
  onStrategy: (strategy: "grid" | "adaptive") => void;
  onDemo: () => void;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onReset: () => void;
  onStep: () => void;
  onSpeed: (speed: number) => void;
}) {
  const [open, setOpen] = useState<DetailId>(null);

  if (!snapshot) {
    return (
      <div className="flex h-full min-h-0 flex-col gap-3">
        <RangePanel />
        <div className="grid flex-1 place-items-center text-base text-muted">Connecting to the simulated mission…</div>
      </div>
    );
  }

  const { mission, robot, probes } = snapshot;
  const probeId =
    probes.length > 0 ? probes[probes.length - 1].id : mission.status === "IDLE" ? "—" : `P${String(probes.length + 1).padStart(2, "0")}`;
  const candidate = mission.candidate;
  const audio = snapshot.sensors.audio;
  const vibration = snapshot.sensors.vibration;
  const fusion = snapshot.sensors.fusion;
  const camera = snapshot.sensors.camera;
  const close = () => setOpen(null);

  const beat = demoNarrationBeat({
    demo: mission.demo_mode,
    status: mission.status,
    phase: mission.phase,
    probeCount: mission.probe_count,
    outcome: mission.outcome,
    scenarioLabel: mission.scenario_label,
    confidence: candidate?.confidence ?? mission.highest_confidence,
    x: candidate?.x ?? robot.x,
    y: candidate?.y ?? robot.y,
  });

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-auto">
      <RangePanel />
      <div className="grid min-h-[640px] shrink-0 grid-rows-[auto_auto_auto_minmax(280px,1fr)_auto] gap-3">
      <div className="border border-line bg-panel px-4 py-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <SummaryCards mission={mission} scenarios={scenarios} onScenario={onScenario} onStrategy={onStrategy} />
          {presentation ? null : (
            <MissionControls
              status={mission.status}
              speed={mission.speed}
              busy={busy}
              onDemo={onDemo}
              onStart={onStart}
              onPause={onPause}
              onResume={onResume}
              onReset={onReset}
              onStep={onStep}
              onSpeed={onSpeed}
            />
          )}
        </div>
      </div>

      {beat ? (
        <TypewriterNarrator
          key={beat.key}
          title={beat.title}
          text={beat.body}
          active={mission.status === "ACTIVE" || mission.status === "COMPLETE" || mission.status === "IDLE"}
          speed={mission.speed}
        />
      ) : (
        <div className="hidden" />
      )}

      {candidate && mission.outcome === "SURVIVOR LOCATION IDENTIFIED" ? (
        <div className="border border-red bg-[#fde8ea] px-4 py-2.5">
          <p className="text-sm font-semibold text-red">Possible find — needs a rescue team to verify</p>
          <div className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-[16px]">
            <span className="num font-semibold">X {candidate.x.toFixed(1)}</span>
            <span className="num font-semibold">Y {candidate.y.toFixed(1)}</span>
            <span className="num font-semibold">{formatPercent(candidate.confidence)}</span>
            <span className="text-sm text-muted">{candidate.status}</span>
          </div>
        </div>
      ) : (
        <div className="hidden" />
      )}

      <RangePanel />

      <div className="grid min-h-0 grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_300px]">
        <Panel title="Map" aside="Hotter color = likelier reply" className="min-h-0 overflow-hidden">
          <SearchMap grid={snapshot.probability_map} robot={robot} probes={probes} candidate={candidate} />
        </Panel>

        <Panel title="Now" aside={probeId} className="min-h-0 overflow-hidden" bodyClassName="flex min-h-0 flex-col gap-3 overflow-auto p-3">
          <ProbeTimeline phase={mission.phase} progress={mission.phase_progress} robotState={mission.robot_state} />
          <dl className="grid grid-cols-2 gap-x-3 gap-y-2">
            <Stat label="Place" value={`${robot.x.toFixed(1)}, ${robot.y.toFixed(1)}`} />
            <Stat label="Battery" value={`${robot.battery.toFixed(0)}%`} />
            <Stat label="Driven" value={`${robot.distance_travelled.toFixed(1)} m`} />
            <Stat label="Knocks" value={String(mission.probe_count)} />
          </dl>
          <ConfidenceGauge value={mission.highest_confidence} />
          <button
            type="button"
            onClick={() => setOpen("why")}
            className="border border-line bg-panel-2 px-3 py-2 text-left hover:border-text"
          >
            <p className="text-sm text-muted">Why</p>
            <p className="mt-1 line-clamp-2 text-sm leading-5 text-text">{snapshot.decision.observation}</p>
            <p className="mt-2 text-xs font-semibold text-orange">Open full note</p>
          </button>
        </Panel>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        <p className="col-span-full text-xs font-semibold tracking-wide text-muted">DEMO MODE · simulated mission cards, not the ultrasonic sensor</p>
        <DetailTile title="Camera" value={camera?.surface_type ?? "No frame"} hint="Open" onOpen={() => setOpen("camera")} />
        <DetailTile
          title="Knock"
          value={vibration ? vibration.confidence.toFixed(2) : "Waiting"}
          hint="Open"
          onOpen={() => setOpen("knock")}
        />
        <DetailTile
          title="Listen"
          value={audio ? audio.confidence.toFixed(2) : "Quiet"}
          hint="Open"
          onOpen={() => setOpen("listen")}
        />
        <DetailTile title="Score mix" value={fusion ? fusion.combined.toFixed(2) : "—"} hint="Open" onOpen={() => setOpen("score")} />
        <DetailTile title="Log" value={`${snapshot.events.length} events`} hint="Open" onOpen={() => setOpen("log")} />
        <DetailTile
          title="Search compare"
          value={
            snapshot.comparison
              ? `${snapshot.comparison.adaptive.measurements} vs ${snapshot.comparison.grid.measurements}`
              : "—"
          }
          hint="Open"
          onOpen={() => setOpen("compare")}
        />
      </div>

      <PopOut title="Camera" aside="Drawn by the sim — not a live feed" open={open === "camera"} onClose={close}>
        <CameraPanel camera={camera} />
      </PopOut>

      <PopOut title="Knock" aside="Vibration after the hit" open={open === "knock"} onClose={close}>
        <WaveformChart
          samples={vibration?.waveform.samples}
          stroke="#1f4b7a"
          empty="Waiting for a knock"
          className="h-[220px]"
        />
        <p className="mt-3 text-sm text-muted">Score {vibration ? vibration.confidence.toFixed(2) : "—"}</p>
      </PopOut>

      <PopOut title="Listen" aside="Sound in the listening window" open={open === "listen"} onClose={close}>
        <WaveformChart samples={audio?.waveform.samples} stroke="#e85d04" empty="No sound yet" className="h-[220px]" />
        <p className="mt-3 text-sm text-muted">Score {audio ? audio.confidence.toFixed(2) : "—"}</p>
      </PopOut>

      <PopOut title="Score mix" aside="How the estimate is weighted" open={open === "score"} onClose={close}>
        <FusionPanel fusion={fusion} />
      </PopOut>

      <PopOut title="Log" aside="What happened in this run" open={open === "log"} onClose={close}>
        <div className="h-[360px] border border-line">
          <EventLog events={snapshot.events} />
        </div>
      </PopOut>

      <PopOut title="Which search is faster?" aside="Sim numbers only" open={open === "compare"} onClose={close}>
        <ComparisonPanel
          comparison={snapshot.comparison}
          liveProbes={mission.probe_count}
          liveDistance={robot.distance_travelled}
        />
      </PopOut>

      <PopOut title="Why this move" open={open === "why"} onClose={close}>
        <p className="text-[16px] leading-7 text-text">{snapshot.decision.observation}</p>
        <p className="mt-4 text-[16px] leading-7 text-muted">{snapshot.decision.decision}</p>
      </PopOut>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="num mt-0.5 text-lg font-semibold">{value}</dd>
    </div>
  );
}
