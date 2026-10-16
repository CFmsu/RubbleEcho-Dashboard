import { useEffect, useState } from "react";
import { SearchMap } from "../components/map/SearchMap";
import { Panel } from "../components/common/Panel";
import type { ScenarioPreset, SimulationConfig, TelemetrySnapshot } from "../types/mission";

const PRESETS = [
  { id: "turkiye_earthquake", title: "Scenario 1", name: "Türkiye Earthquake Rubble" },
  { id: "nepal_earthquake", title: "Scenario 2", name: "Nepal Earthquake Debris" },
  { id: "nepal_flood", title: "Scenario 3", name: "Nepal Flash Flood Debris" },
  { id: "structural_collapse", title: "Scenario 4", name: "Generic Structural Collapse" },
];

export function MissionSimulation({
  snapshot,
  scenarios,
  onGenerate,
}: {
  snapshot: TelemetrySnapshot | null;
  scenarios: ScenarioPreset[];
  onGenerate: (config: SimulationConfig) => void;
}) {
  const [form, setForm] = useState<SimulationConfig | null>(null);

  useEffect(() => {
    if (!form && scenarios.length > 0) {
      const preset = scenarios.find((item) => item.id === "structural_collapse") ?? scenarios[0];
      setForm(toConfig(preset, snapshot?.mission.search_strategy ?? "adaptive", snapshot?.mission.speed ?? 1));
    }
  }, [form, scenarios, snapshot]);

  if (!form) {
    return <div className="text-sm text-muted">Loading simulation scenarios…</div>;
  }

  const set = <K extends keyof SimulationConfig>(key: K, value: SimulationConfig[K]) => {
    setForm({ ...form, [key]: value });
  };

  return (
    <div className="mx-auto grid max-w-6xl gap-3 lg:grid-cols-[1.1fr_0.9fr]">
      <Panel title="Simulation environment" aside="Ground truth stays off the search path" bodyClassName="p-4">
        <p className="mb-4 text-[13px] leading-5 text-muted">
          These are simulation scenarios inspired by disaster-response conditions. They are not reconstructions of individual sites or victims.
          The hidden source is known only to the environment simulator.
        </p>
        <div className="mb-4 grid gap-2 sm:grid-cols-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className="border border-line bg-panel-2 px-3 py-2 text-left hover:border-[#3d4d64]"
              onClick={() => {
                const match = scenarios.find((item) => item.id === preset.id);
                if (match) setForm(toConfig(match, form.search_strategy, form.speed));
              }}
            >
              <div className="text-[10px] uppercase tracking-[0.14em] text-muted">{preset.title}</div>
              <div className="text-[13px]">{preset.name}</div>
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3 text-[13px]">
          <Field label="Environment width" value={form.width} min={6} max={24} step={1} onChange={(value) => set("width", value)} />
          <Field label="Environment height" value={form.height} min={6} max={24} step={1} onChange={(value) => set("height", value)} />
          <Field label="Hidden survivor X" value={form.survivor_x} min={0.5} max={form.width - 0.5} step={0.1} onChange={(value) => set("survivor_x", value)} />
          <Field label="Hidden survivor Y" value={form.survivor_y} min={0.5} max={form.height - 0.5} step={0.1} onChange={(value) => set("survivor_y", value)} />
          <Field label="Noise level" value={form.noise_level} min={0} max={1} step={0.01} onChange={(value) => set("noise_level", value)} />
          <Field label="Response probability" value={form.response_probability} min={0} max={1} step={0.01} onChange={(value) => set("response_probability", value)} />
          <Field label="Sensor reliability" value={form.sensor_reliability} min={0} max={1} step={0.01} onChange={(value) => set("sensor_reliability", value)} />
          <Field label="Random seed" value={form.seed} min={0} max={99999} step={1} onChange={(value) => set("seed", value)} />
        </div>
        <label className="mt-3 block text-[12px] text-muted">
          Search strategy
          <select
            className="mt-1 w-full border border-line bg-bg px-2 py-1.5 text-text"
            value={form.search_strategy}
            onChange={(event) => set("search_strategy", event.target.value as SimulationConfig["search_strategy"])}
          >
            <option value="adaptive">Adaptive search</option>
            <option value="grid">Grid search</option>
          </select>
        </label>
        <button type="button" className="cmd primary mt-4" onClick={() => onGenerate(form)}>
          Generate Scenario
        </button>
      </Panel>
      <Panel title="Scenario preview" aside="Engineering view" bodyClassName="p-2">
        <p className="px-2 pb-2 text-[12px] leading-5 text-muted">
          The green mark is ground truth for setup only. It is not published on mission telemetry and is not given to the search algorithm.
        </p>
        <div className="h-[420px]">
          <SearchMap
            grid={emptyGrid(form.width, form.height)}
            robot={null}
            probes={[]}
            candidate={null}
            groundTruth={{ x: form.survivor_x, y: form.survivor_y }}
          />
        </div>
      </Panel>
    </div>
  );
}

function emptyGrid(width: number, height: number): number[][] {
  const value = 1 / (width * height);
  return Array.from({ length: height }, () => Array.from({ length: width }, () => value));
}

function toConfig(preset: ScenarioPreset, strategy: SimulationConfig["search_strategy"], speed: number): SimulationConfig {
  return {
    width: preset.width,
    height: preset.height,
    survivor_x: preset.survivor_x,
    survivor_y: preset.survivor_y,
    noise_level: preset.noise_level,
    response_probability: preset.response_probability,
    sensor_reliability: preset.sensor_reliability,
    search_strategy: strategy,
    seed: preset.seed,
    scenario: preset.id,
    speed,
    demo_mode: false,
  };
}

function Field({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-[12px] text-muted">
      {label}
      <input
        className="num mt-1 w-full border border-line bg-bg px-2 py-1.5 text-text"
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
