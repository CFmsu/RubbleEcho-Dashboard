const FLOW = [
  "Physical environment",
  "RubbleEcho robot",
  "Sensors — camera, microphone, piezo, striker",
  "Edge processing",
  "Sensor fusion",
  "Search map",
  "Next probe choice",
  "Next probe selection",
  "Robot navigation",
  "Human rescue team",
];

const STATUS = [
  ["Simulation engine", "ACTIVE"],
  ["Mission dashboard", "ACTIVE"],
  ["Adaptive search", "PROTOTYPE"],
  ["Physical robot", "PENDING"],
  ["Piezo hardware", "PENDING"],
  ["Microphone hardware", "PENDING"],
  ["Striker hardware", "PENDING"],
  ["Optional cloud model", "FIELD PAGE"],
  ["Hosted demo", "PLANNED"],
  ["Field validation", "FUTURE"],
];

export function Architecture() {
  return (
    <div className="mx-auto grid max-w-6xl gap-3 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="border border-line bg-panel p-4">
        <h2 className="text-[11px] uppercase tracking-[0.16em] text-muted">Data flow</h2>
        <ol className="mt-4">
          {FLOW.map((item, index) => (
            <li key={item} className="relative pb-4 pl-8">
              {index < FLOW.length - 1 ? <span className="absolute left-[7px] top-3 h-full w-px bg-line" /> : null}
              <span className="absolute left-0 top-1 h-3.5 w-3.5 border border-blue bg-bg" />
              <div className="text-[14px]">{item}</div>
            </li>
          ))}
        </ol>
      </section>
      <div className="grid content-start gap-3">
        <section className="border border-line bg-panel p-4">
          <h2 className="text-[11px] uppercase tracking-[0.16em] text-muted">Implementation boundary</h2>
          <p className="mt-3 text-[14px] leading-6">
            Current implementation: simulation.
          </p>
          <p className="mt-2 text-[14px] leading-6 text-muted">
            Later hardware swaps in behind the same adapters: motion, camera, microphone, piezo, and striker. The Field page can call a cloud model when a key is set. The simulated mission does not.
          </p>
          <div className="mt-4 grid gap-2 text-[13px]">
            <Adapter name="MotionAdapter" now="SimulatedMotionAdapter" later="ESP32MotionAdapter" />
            <Adapter name="CameraAdapter" now="SimulatedCameraAdapter" later="USBCameraAdapter" />
            <Adapter name="MicrophoneAdapter" now="SimulatedMicrophoneAdapter" later="Edge audio capture" />
            <Adapter name="PiezoAdapter" now="SimulatedPiezoAdapter" later="SerialPiezoAdapter" />
            <Adapter name="StrikerAdapter" now="SimulatedStrikerAdapter" later="GPIOStrikerAdapter" />
            <Adapter name="ReasoningProvider" now="SimulatedReasoningProvider" later="NvidiaReasoningProvider" />
          </div>
        </section>
        <section className="border border-line bg-panel p-4">
          <h2 className="text-[11px] uppercase tracking-[0.16em] text-muted">Project status</h2>
          <ul className="mt-3 grid gap-1.5 text-[13px]">
            {STATUS.map(([name, state]) => (
              <li key={name} className="flex justify-between gap-3 border-b border-line/80 py-1">
                <span>{name}</span>
                <span className="tracking-[0.08em] text-muted">{state}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[12px] leading-5 text-muted">
            The simulated mission uses local template text. A cloud model is used only from the Field page, and only when a key is present.
          </p>
        </section>
      </div>
    </div>
  );
}

function Adapter({ name, now, later }: { name: string; now: string; later: string }) {
  return (
    <div className="border border-line px-2 py-1.5">
      <div className="font-mono text-[12px]">{name}</div>
      <div className="text-[12px] text-muted">Now: {now}</div>
      <div className="text-[12px] text-muted">Later: {later}</div>
    </div>
  );
}
