import type { HardwareItem } from "../../types/mission";

function tone(status: string): string {
  if (status === "SIMULATED" || status === "STANDBY") return "text-yellow";
  if (status === "FIRING" || status === "LISTENING") return "text-cyan";
  return "text-green";
}

export function HardwarePanel({ items }: { items: HardwareItem[] }) {
  return (
    <ul className="grid h-full content-center gap-1 px-2.5 text-[12px]">
      {items.map((item) => (
        <li key={item.name} className="flex justify-between gap-3">
          <span className="text-muted">{item.name}</span>
          <span className={`tracking-[0.08em] ${tone(item.status)}`}>{item.status}</span>
        </li>
      ))}
    </ul>
  );
}
