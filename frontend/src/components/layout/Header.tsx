import type { ConnectionStatus } from "../../types/mission";

export function Header({
  backendOk,
  connection,
  missionStatus,
  operatingMode,
}: {
  backendOk: boolean;
  connection: ConnectionStatus;
  missionStatus: string;
  operatingMode: "demo" | "real";
}) {
  const linkOk = backendOk && connection === "connected";
  return (
    <header className="shrink-0 border-b border-line bg-panel px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-extrabold leading-none tracking-tight text-text">RubbleEcho</h1>
          <p className="mt-1.5 max-w-xl text-[15px] text-muted">
            Dashboard for the RubbleEcho rover. The live run is a simulation. Field mode uses photographs and connected hardware only.
          </p>
        </div>
        <div className="text-right text-sm">
          <p className="font-bold text-orange">{operatingMode === "real" ? "Real mode" : "Demo mode"}</p>
          <p className="mt-1 text-muted">
            Link {linkOk ? "online" : "offline"} · Mission {missionStatus.toLowerCase()}
          </p>
        </div>
      </div>
    </header>
  );
}
