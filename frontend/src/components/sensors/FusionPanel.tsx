import type { FusionResult } from "../../types/mission";
import { formatFixed } from "../../utils/format";

const ROWS: Array<{ key: keyof Pick<FusionResult, "audio" | "vibration" | "cavity" | "visual">; label: string; weight: string }> = [
  { key: "audio", label: "Sound after knock", weight: "35%" },
  { key: "vibration", label: "Shake in the rubble", weight: "30%" },
  { key: "cavity", label: "Hollow space hint", weight: "20%" },
  { key: "visual", label: "Camera clue", weight: "15%" },
];

export function FusionPanel({ fusion }: { fusion: FusionResult | null }) {
  return (
    <div className="flex h-full flex-col justify-center gap-2.5 p-4 text-[15px]">
      {ROWS.map((row) => (
        <div key={row.key} className="grid grid-cols-[1fr_auto_auto] items-center gap-3">
          <span className="text-muted">{row.label}</span>
          <span className="text-sm text-muted">{row.weight}</span>
          <span className="num w-12 text-right font-semibold">{fusion ? formatFixed(fusion[row.key]) : "—"}</span>
        </div>
      ))}
      <div className="mt-1 grid grid-cols-[1fr_auto] border-t border-line pt-2 font-bold">
        <span>Combined</span>
        <span className="num">{fusion ? formatFixed(fusion.combined) : "—"}</span>
      </div>
    </div>
  );
}
