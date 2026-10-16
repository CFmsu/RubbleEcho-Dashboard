import type { RobotState } from "../../types/mission";
import { ProbeTimeline } from "./ProbeTimeline";

export function RobotStatus({
  robot,
  phase,
  progress,
  probeId,
}: {
  robot: RobotState;
  phase: string;
  progress: number;
  probeId: string;
}) {
  return (
    <div className="flex h-full flex-col justify-between px-2.5 py-2">
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[12px]">
        <Field label="Current activity" value={phase.replaceAll("_", " ")} />
        <Field label="Current probe" value={probeId} />
        <Field label="Position" value={`X ${robot.x.toFixed(1)}   Y ${robot.y.toFixed(1)}`} mono />
        <Field label="Heading" value={`${robot.heading.toFixed(0)}°`} mono />
        <Field label="Velocity" value={`${robot.velocity.toFixed(2)} m/s`} mono />
        <Field label="Distance" value={`${robot.distance_travelled.toFixed(1)} m`} mono />
      </div>
      <div>
        <div className="mb-1 flex justify-between text-[10px] uppercase tracking-[0.12em] text-muted">
          <span>Battery</span>
          <span className="num text-text">{robot.battery.toFixed(0)}%</span>
        </div>
        <div className="h-1.5 bg-[#e4ebf3]">
          <div className="h-full bg-green" style={{ width: `${robot.battery}%` }} />
        </div>
      </div>
      <ProbeTimeline phase={phase} progress={progress} />
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.12em] text-muted">{label}</div>
      <div className={mono ? "num" : ""}>{value}</div>
    </div>
  );
}
