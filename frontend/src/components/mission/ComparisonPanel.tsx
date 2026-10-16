import type { ComparisonResult } from "../../types/mission";

export function ComparisonPanel({
  comparison,
  liveProbes,
  liveDistance,
}: {
  comparison: ComparisonResult | null;
  liveProbes: number;
  liveDistance: number;
}) {
  return (
    <div className="flex h-full flex-col p-4">
      <p className="text-sm text-muted">Same scene, two search styles — numbers from the simulator.</p>
      <div className="mt-3 grid flex-1 grid-cols-2 gap-5">
        <Column title="Grid sweep" stats={comparison?.grid} />
        <Column title="Smart path" stats={comparison?.adaptive} />
      </div>
      <p className="mt-3 text-sm text-muted">
        This live run: {liveProbes} knocks, {liveDistance.toFixed(1)} m driven.
      </p>
    </div>
  );
}

function Column({
  title,
  stats,
}: {
  title: string;
  stats?: { measurements: number; distance_travelled: number; simulated_minutes: number };
}) {
  return (
    <div>
      <h3 className="text-[15px] font-bold">{title}</h3>
      <p className="num mt-2 text-xl">{stats ? stats.measurements : "—"}</p>
      <p className="text-sm text-muted">knocks</p>
      <p className="num mt-2 text-[15px]">{stats ? `${stats.distance_travelled.toFixed(1)} m` : "—"}</p>
      <p className="num text-[15px] text-muted">{stats ? `${stats.simulated_minutes.toFixed(1)} min` : "—"}</p>
    </div>
  );
}
