import type { CameraObservation } from "../../types/mission";

export function CameraPanel({ camera }: { camera: CameraObservation | null }) {
  const density = camera?.debris_density ?? 0.35;
  const voidVisible = Boolean(camera?.visible_void);
  return (
    <div className="grid h-full min-h-0 gap-4 md:grid-cols-[220px_minmax(0,1fr)]">
      <div className="relative min-h-[180px] border border-line bg-[#edf1f5]">
        <svg viewBox="0 0 80 80" className="h-full w-full" aria-label="Drawn camera preview">
          <rect width="80" height="80" fill="#f4f6f8" />
          <rect x="0" y="50" width="80" height="30" fill="#d9e0e8" />
          <polygon points="0,52 18,32 32,46 50,24 68,42 80,30 80,80 0,80" fill="#8f9eae" />
          <polygon points="8,80 22,44 34,80" fill="#6f8092" opacity={0.7 + density * 0.2} />
          <polygon points="40,80 54,38 72,80" fill="#5a6b7c" opacity={0.6 + density * 0.25} />
          <rect x="24" y="36" width="18" height="11" fill="#4d5d6d" transform="rotate(-14 33 41)" />
          {voidVisible ? <ellipse cx="58" cy="60" rx="8" ry="6" fill="#2f3b48" /> : <rect x="52" y="56" width="14" height="8" fill="#7d8c9c" />}
        </svg>
        <span className="absolute bottom-1 left-1 bg-white px-1.5 py-0.5 text-xs font-semibold text-muted">Drawn view</span>
      </div>
      <dl className="grid content-start gap-3 text-[15px]">
        <Row label="Surface" value={camera?.surface_type ?? "—"} />
        <Row label="Debris" value={camera ? camera.debris_density.toFixed(2) : "—"} mono />
        <Row label="Opening" value={camera ? (camera.visible_void ? "Maybe" : "None seen") : "—"} />
        <Row label="Safe to knock?" value={camera ? (camera.safe_to_probe ? "Yes" : "Careful") : "—"} />
        <p className="pt-1 text-sm leading-5 text-muted">
          {camera?.note ?? "No frame yet. This is a picture the sim draws — not a real camera."}
        </p>
      </dl>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line pb-2">
      <dt className="text-muted">{label}</dt>
      <dd className={`capitalize ${mono ? "num" : "font-semibold"}`}>{value}</dd>
    </div>
  );
}
