import { formatPercent } from "../../utils/format";

function plainBand(value: number): string {
  if (value >= 0.75) return "Strong signal";
  if (value >= 0.5) return "Worth checking";
  if (value >= 0.25) return "Weak hint";
  return "Quiet so far";
}

export function ConfidenceGauge({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted">Estimated chance</p>
          <p className="mt-0.5 text-sm text-muted">From the sensors in this simulation</p>
        </div>
        <span className="num text-4xl font-medium leading-none">{formatPercent(value)}</span>
      </div>
      <div className="mt-3 h-3 bg-panel-2">
        <div className="h-full bg-orange" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 text-[15px] font-semibold">{plainBand(value)}</p>
    </div>
  );
}
