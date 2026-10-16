import { useCallback, useState } from "react";
import { getJson, postJson } from "../services/api";
import type { LabResult, ScenarioPreset, SimulationConfig } from "../types/mission";

export function useMission() {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = useCallback(async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }, []);

  return {
    error,
    busy,
    clearError: () => setError(null),
    start: () => run(() => postJson("/api/mission/start")),
    demo: () => run(() => postJson("/api/mission/demo")),
    pause: () => run(() => postJson("/api/mission/pause")),
    resume: () => run(() => postJson("/api/mission/resume")),
    reset: () => run(() => postJson("/api/mission/reset")),
    step: () => run(() => postJson("/api/mission/step")),
    setSpeed: (speed: number) => run(() => postJson("/api/mission/speed", { speed })),
    configure: (config: SimulationConfig) => run(() => postJson("/api/simulation/config", config)),
    scenarios: () => getJson<{ scenarios: ScenarioPreset[] }>("/api/scenarios"),
    config: () => getJson<{ config: SimulationConfig; note: string }>("/api/simulation/config"),
    stimulus: (stimulus: string) => postJson<LabResult>("/api/lab/stimulus", { stimulus }),
  };
}
