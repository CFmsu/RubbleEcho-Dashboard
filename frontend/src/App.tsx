import { useEffect, useRef, useState } from "react";
import { Header } from "./components/layout/Header";
import { Nav } from "./components/layout/Nav";
import { useMission } from "./hooks/useMission";
import { useTelemetry } from "./hooks/useTelemetry";
import { About } from "./pages/About";
import { Architecture } from "./pages/Architecture";
import { Dashboard } from "./pages/Dashboard";
import { Field } from "./pages/Field";
import { MissionSimulation } from "./pages/MissionSimulation";
import { BenchTest } from "./pages/BenchTest";
import { SensorLab } from "./pages/SensorLab";
import { getJson, postJson } from "./services/api";
import type { PageId, ScenarioPreset, SimulationConfig } from "./types/mission";

export function App() {
  const { snapshot, connection } = useTelemetry();
  const mission = useMission();
  const [page, setPage] = useState<PageId>("dashboard");
  const [presentation, setPresentation] = useState(false);
  const [backendOk, setBackendOk] = useState(false);
  const [scenarios, setScenarios] = useState<ScenarioPreset[]>([]);
  const [operatingMode, setOperatingMode] = useState<"demo" | "real">("demo");

  useEffect(() => {
    let stop = false;
    const poll = async () => {
      try {
        const health = await getJson<{ status: string }>("/api/health");
        if (!stop) setBackendOk(health.status === "ok");
      } catch {
        if (!stop) setBackendOk(false);
      }
    };
    void poll();
    const id = window.setInterval(() => void poll(), 4000);
    return () => {
      stop = true;
      window.clearInterval(id);
    };
  }, []);

  useEffect(() => {
    let stop = false;
    const load = async () => {
      try {
        const result = await getJson<{ scenarios: ScenarioPreset[] }>("/api/scenarios");
        if (!stop) setScenarios(result.scenarios);
      } catch {
        if (!stop) setScenarios([]);
      }
    };
    if (backendOk) void load();
    return () => {
      stop = true;
    };
  }, [backendOk]);

  useEffect(() => {
    if (!backendOk || scenarios.length > 0) return;
    const id = window.setInterval(() => {
      void getJson<{ scenarios: ScenarioPreset[] }>("/api/scenarios")
        .then((result) => {
          if (result.scenarios.length > 0) setScenarios(result.scenarios);
        })
        .catch(() => undefined);
    }, 2500);
    return () => window.clearInterval(id);
  }, [backendOk, scenarios.length]);

  const snapshotRef = useRef(snapshot);
  const missionRef = useRef(mission);
  snapshotRef.current = snapshot;
  missionRef.current = mission;

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      const status = snapshotRef.current?.mission.status;
      const actions = missionRef.current;
      if (event.key === "p" || event.key === "P") {
        event.preventDefault();
        setPresentation((value) => !value);
        setPage("dashboard");
      } else if (event.key === " ") {
        event.preventDefault();
        if (status === "ACTIVE") void actions.pause();
        else if (status === "PAUSED") void actions.resume();
      } else if (event.key === "n" || event.key === "N") {
        void actions.step();
      } else if (event.key === "r" || event.key === "R") {
        void actions.reset();
      } else if (event.key === "d" || event.key === "D") {
        setPage("dashboard");
        void actions.demo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!backendOk) return;
    let stop = false;
    void getJson<{ operating_mode: "demo" | "real" }>("/api/mode")
      .then((result) => {
        if (!stop) setOperatingMode(result.operating_mode);
      })
      .catch(() => undefined);
    return () => {
      stop = true;
    };
  }, [backendOk]);

  const setMode = (mode: "demo" | "real") => {
    void postJson("/api/mode", { operating_mode: mode })
      .then(() => {
        setOperatingMode(mode);
        if (mode === "real") setPage("field");
      })
      .catch(() => undefined);
  };

  const applyScenario = (id: string) => {
    const preset = scenarios.find((item) => item.id === id);
    if (!preset || !snapshot) return;
    const config: SimulationConfig = {
      width: preset.width,
      height: preset.height,
      survivor_x: preset.survivor_x,
      survivor_y: preset.survivor_y,
      noise_level: preset.noise_level,
      response_probability: preset.response_probability,
      sensor_reliability: preset.sensor_reliability,
      search_strategy: snapshot.mission.search_strategy,
      seed: preset.seed,
      scenario: preset.id,
      speed: snapshot.mission.speed,
      demo_mode: false,
    };
    void mission.configure(config);
  };

  const applyStrategy = (strategy: "grid" | "adaptive") => {
    if (!snapshot) return;
    const preset = scenarios.find((item) => item.id === snapshot.mission.scenario);
    const config: SimulationConfig = {
      width: preset?.width ?? snapshot.mission.width,
      height: preset?.height ?? snapshot.mission.height,
      survivor_x: preset?.survivor_x ?? 7.2,
      survivor_y: preset?.survivor_y ?? 6.4,
      noise_level: preset?.noise_level ?? 0.16,
      response_probability: preset?.response_probability ?? 0.72,
      sensor_reliability: preset?.sensor_reliability ?? 0.9,
      search_strategy: strategy,
      seed: preset?.seed ?? 42,
      scenario: snapshot.mission.scenario,
      speed: snapshot.mission.speed,
      demo_mode: false,
    };
    void mission.configure(config);
  };

  const disconnected = connection !== "connected" || !backendOk;

  return (
    <div className="flex h-full flex-col bg-bg text-text">
      <Header
        backendOk={backendOk}
        connection={connection}
        missionStatus={snapshot?.mission.status ?? "STANDBY"}
        operatingMode={operatingMode}
      />
      {presentation ? null : <Nav page={page} onChange={setPage} />}
      {disconnected ? (
        <div className="border-b border-red bg-[#fde8ea] px-5 py-2.5 text-[15px] text-red">
          Backend is offline. Trying to reconnect…
        </div>
      ) : null}
      {mission.error ? (
        <div className="border-b border-orange bg-[#fff1e7] px-5 py-2.5 text-[15px] text-orange">{mission.error}</div>
      ) : null}
      <main className="flex min-h-0 flex-1 flex-col overflow-hidden p-4">
        {page === "dashboard" || presentation ? (
          <div className="flex min-h-0 flex-1 flex-col gap-3">
            <p className="shrink-0 border border-line bg-[#fff1e7] px-4 py-2 text-sm">
              DEMO MODE. The map, waveforms, and confidence on this page are simulated. They are not field measurements.
            </p>
            <div className="min-h-0 flex-1">
            <Dashboard
              snapshot={snapshot}
              scenarios={scenarios}
              presentation={presentation}
              busy={mission.busy}
              onScenario={applyScenario}
              onStrategy={applyStrategy}
              onDemo={() => void mission.demo()}
              onStart={() => void mission.start()}
              onPause={() => void mission.pause()}
              onResume={() => void mission.resume()}
              onReset={() => void mission.reset()}
              onStep={() => void mission.step()}
              onSpeed={(speed) => void mission.setSpeed(speed)}
            />
            </div>
          </div>
        ) : null}
        {page === "field" && !presentation ? (
          <div className="min-h-0 flex-1 overflow-hidden">
            <Field operatingMode={operatingMode} onMode={setMode} />
          </div>
        ) : null}
        {page === "simulation" && !presentation ? (
          <div className="min-h-0 flex-1 overflow-auto">
            <MissionSimulation snapshot={snapshot} scenarios={scenarios} onGenerate={(config) => void mission.configure(config)} />
          </div>
        ) : null}
        {page === "lab" && !presentation ? (
          <div className="min-h-0 flex-1 overflow-auto">
            <SensorLab
              onOpenBench={() => setPage("bench")}
              onStimulus={async (name) => {
                try {
                  return await mission.stimulus(name);
                } catch {
                  return null;
                }
              }}
            />
          </div>
        ) : null}
        {page === "bench" && !presentation ? (
          <div className="min-h-0 flex-1 overflow-auto">
            <BenchTest />
          </div>
        ) : null}
        {page === "architecture" && !presentation ? (
          <div className="min-h-0 flex-1 overflow-auto">
            <Architecture />
          </div>
        ) : null}
        {page === "about" && !presentation ? (
          <div className="min-h-0 flex-1 overflow-auto">
            <About />
          </div>
        ) : null}
      </main>
      {presentation ? (
        <div className="px-5 py-2 text-[15px] text-muted">Press P to leave presentation</div>
      ) : null}
    </div>
  );
}
