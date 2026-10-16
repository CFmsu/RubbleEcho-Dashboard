const STEPS = ["Move", "Stop", "Touch", "Knock", "Listen", "Measure", "Think", "Update map", "Pick next"];

function activeIndex(phase: string, progress: number): number {
  if (phase === "CONTACT") return progress < 0.45 ? 1 : 2;
  if (phase === "LISTENING") return progress < 0.55 ? 4 : 5;
  const map: Record<string, number> = {
    IDLE: 0,
    NAVIGATING: 0,
    KNOCKING: 3,
    ANALYZING: 6,
    UPDATING_MAP: 7,
    SELECTING_TARGET: 8,
    CONFIRMING: 8,
    HUMAN_RESPONSE_DETECTED: 6,
    LOCATION_IDENTIFIED: 8,
  };
  return map[phase] ?? 0;
}

function plainState(phase: string, robotState: string): string {
  const byPhase: Record<string, string> = {
    IDLE: "Waiting to start",
    NAVIGATING: "Driving to the next spot",
    CONTACT: "Touching the rubble",
    KNOCKING: "Knocking on the structure",
    LISTENING: "Listening for a reply",
    ANALYZING: "Checking the sensor data",
    UPDATING_MAP: "Updating the map",
    SELECTING_TARGET: "Choosing the next spot",
    CONFIRMING: "Double-checking this spot",
    HUMAN_RESPONSE_DETECTED: "Possible reply heard",
    LOCATION_IDENTIFIED: "Candidate spot found",
  };
  return byPhase[phase] ?? robotState.replaceAll("_", " ").toLowerCase();
}

export function ProbeTimeline({
  phase,
  progress,
  robotState = "",
}: {
  phase: string;
  progress: number;
  robotState?: string;
}) {
  const current = activeIndex(phase, progress);
  return (
    <div>
      <p className="text-xl font-extrabold leading-tight tracking-tight">{plainState(phase, robotState)}</p>
      <ol className="mt-2 flex flex-wrap gap-1">
        {STEPS.map((step, index) => (
          <li
            key={step}
            className={`px-1.5 py-0.5 text-[11px] font-semibold ${
              index === current
                ? "bg-orange text-white"
                : index < current
                  ? "bg-panel-2 text-text"
                  : "bg-panel-2 text-muted"
            }`}
          >
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}
