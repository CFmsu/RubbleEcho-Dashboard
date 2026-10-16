import { useEffect, useRef } from "react";
import type { MissionEvent } from "../../types/mission";
import { formatRuntime } from "../../utils/format";

const LEVEL: Record<MissionEvent["level"], string> = {
  info: "text-text",
  warn: "text-yellow",
  alert: "text-red",
  good: "text-green",
};

export function EventLog({ events }: { events: MissionEvent[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [events]);

  return (
    <div ref={ref} className="h-full overflow-auto px-3 py-2 font-mono text-sm leading-5">
      {events.length === 0 ? <p className="text-muted">No mission events yet.</p> : null}
      {events.map((event, index) => (
        <div key={`${event.time}-${index}`} className="grid grid-cols-[44px_1fr] gap-2">
          <span className="text-muted">{formatRuntime(event.time)}</span>
          <span className={LEVEL[event.level]}>{event.message}</span>
        </div>
      ))}
    </div>
  );
}
