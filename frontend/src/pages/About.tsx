const STREAMS: Array<{ title: string; items: string[] }> = [
  { title: "Software", items: ["Simulation", "Dashboard", "Backend", "Telemetry"] },
  { title: "Robotics", items: ["Mobility", "Mechanical striker", "Mounting", "Power"] },
  { title: "Sensing", items: ["Microphone", "Piezo", "Camera", "Radar research"] },
  { title: "Search logic", items: ["Signal processing", "Sensor fusion", "Search map", "Next probe"] },
  { title: "Infrastructure", items: ["Hosting", "Logging", "Deployment", "Serial link"] },
  { title: "Validation", items: ["Test environment", "Controlled rubble", "Metrics", "Experiments"] },
];

const STEPS = [
  "Explore the search area",
  "Stop at a probe location",
  "Knock on the surface",
  "Listen for a response",
  "Score the simulated signals",
  "Update the search map",
  "Pick the next probe location",
  "Repeat the search process",
  "Mark a location for human verification",
];
export function About() {
  return (
    <div className="mx-auto grid max-w-5xl gap-3">
      <section className="border border-line bg-panel p-5">
        <p className="text-[11px] uppercase tracking-[0.16em] text-muted">McNeeseNexus</p>
        <h2 className="mt-2 text-2xl font-medium">RubbleEcho</h2>
        <p className="mt-1 text-muted">Dashboard for the RubbleEcho rover. ACM 2026 hackathon.</p>
        <p className="mt-1 text-[13px] tracking-[0.08em] text-yellow">Knock. Listen. Locate.</p>
        <p className="mt-4 max-w-3xl text-[15px] leading-7">
        After a building collapses, much of the search area is hidden beneath debris. A trapped person may not be visible or able to call for help, but they might respond to a knock. RubbleEcho explores the idea of using knocks, listening, and simulated sensor readings to decide where to search next.
        </p>
        <p className="mt-3 max-w-3xl text-[14px] leading-6 text-muted">
        RubbleEcho is currently a software simulation, not a physical robot or a working rescue sensor. Its readings and confidence scores are simulated estimates, not verified measurements. It cannot locate real people and must not be used to make rescue decisions.
        </p>
      </section>
      <section className="border border-line bg-panel p-5">
        <h2 className="text-[11px] uppercase tracking-[0.16em] text-muted">Workstreams</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {STREAMS.map((stream) => (
            <div key={stream.title} className="border border-line p-3">
              <h3 className="text-[12px] uppercase tracking-[0.14em]">{stream.title}</h3>
              <ul className="mt-2 space-y-1 text-[13px] text-muted">
                {stream.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
      <section className="border border-line bg-panel p-5">
        <h2 className="text-[11px] uppercase tracking-[0.16em] text-muted">How the rover searches.</h2>
        <ol className="mt-4 grid gap-2 sm:grid-cols-2">
          {STEPS.map((step, index) => (
            <li key={step} className="flex gap-3 text-[14px]">
              <span className="num text-muted">{String(index + 1).padStart(2, "0")}</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </section>
      <section className="border border-line bg-panel p-5">
  <h2 className="text-[11px] uppercase tracking-[0.16em] text-muted">
    Hardware later
  </h2>
  <p className="mt-3 text-[14px] leading-6 text-muted">
    These are planned hardware components for future development.
    They are not connected to the current simulation.
  </p>
  <div className="mt-4 grid gap-3 sm:grid-cols-2">
    {["Robot chassis", "Knock mechanism", "Microphone and piezo sensors", "Camera"].map((item) => (
      <div key={item} className="border border-line p-3">
        <h3 className="text-[14px] font-medium">{item}</h3>
        <p className="mt-2 text-[13px] text-muted">Not connected</p>
      </div>
    ))}
  </div>
</section>
    </div>
  );
}
