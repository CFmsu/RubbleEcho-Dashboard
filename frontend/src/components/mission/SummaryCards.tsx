import type { ReactNode } from "react";
import type { MissionView, ScenarioPreset } from "../../types/mission";
import { formatRuntime } from "../../utils/format";

export function SummaryCards({
  mission,
  scenarios,
  onScenario,
  onStrategy,
}: {
  mission: MissionView;
  scenarios: ScenarioPreset[];
  onScenario: (id: string) => void;
  onStrategy: (strategy: "grid" | "adaptive") => void;
}) {
  const locked = mission.status === "ACTIVE" || mission.status === "PAUSED";
  const choices = scenarios.length > 0 ? scenarios : [{ id: mission.scenario, label: mission.scenario_label }];

  return (
    <div className="flex flex-wrap items-end gap-4">
      <Field label="Run">
        <span className="num text-[17px] font-semibold">{mission.id}</span>
      </Field>
      <Field label="Scene">
        <select
          className="field min-w-[200px]"
          value={choices.some((item) => item.id === mission.scenario) ? mission.scenario : choices[0].id}
          disabled={locked || scenarios.length === 0}
          onChange={(event) => onScenario(event.target.value)}
          aria-label="Scene"
        >
          {choices.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Search style">
        <select
          className="field"
          value={mission.search_strategy}
          disabled={locked}
          onChange={(event) => onStrategy(event.target.value as "grid" | "adaptive")}
          aria-label="Search style"
        >
          <option value="adaptive">Smart path</option>
          <option value="grid">Grid sweep</option>
        </select>
      </Field>
      <Field label="Clock">
        <span className="num text-[17px]">{formatRuntime(mission.runtime)}</span>
      </Field>
      <Field label="Kind">
        <span className="text-[15px] font-semibold text-muted">{mission.demo_mode ? "Guided demo" : "Free search"}</span>
      </Field>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm text-muted">{label}</span>
      {children}
    </label>
  );
}
