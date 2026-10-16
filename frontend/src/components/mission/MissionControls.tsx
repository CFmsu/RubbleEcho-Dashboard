const SPEEDS = [0.5, 1, 2, 5, 10];

export function MissionControls({
  status,
  speed,
  busy,
  onDemo,
  onStart,
  onPause,
  onResume,
  onReset,
  onStep,
  onSpeed,
}: {
  status: string;
  speed: number;
  busy: boolean;
  onDemo: () => void;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onReset: () => void;
  onStep: () => void;
  onSpeed: (speed: number) => void;
}) {
  const running = status === "ACTIVE";
  const paused = status === "PAUSED";
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" className="cmd primary" disabled={busy} onClick={onDemo}>
        Play demo
      </button>
      <button type="button" className="cmd" disabled={busy || running} onClick={onStart}>
        Start search
      </button>
      <button type="button" className="cmd" disabled={busy || (!running && !paused)} onClick={running ? onPause : onResume}>
        {paused ? "Resume" : "Pause"}
      </button>
      <button type="button" className="cmd" disabled={busy || status === "IDLE" || status === "COMPLETE"} onClick={onStep}>
        One step
      </button>
      <button type="button" className="cmd" disabled={busy} onClick={onReset}>
        Reset
      </button>
      <span className="mx-1 hidden h-5 w-px bg-line sm:inline-block" />
      <span className="text-sm text-muted">Speed</span>
      {SPEEDS.map((value) => (
        <button key={value} type="button" className={`cmd ${speed === value ? "active" : ""}`} onClick={() => onSpeed(value)}>
          {value}×
        </button>
      ))}
    </div>
  );
}
