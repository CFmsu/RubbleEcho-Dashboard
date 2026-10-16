const STREAMS: Array<{ title: string; items: string[] }> = [
  { title: "Software", items: ["Simulation", "Dashboard", "Backend", "Telemetry"] },
  { title: "Robotics", items: ["Mobility", "Mechanical striker", "Mounting", "Power"] },
  { title: "Sensing", items: ["Microphone", "Piezo", "Camera", "Radar research"] },
  { title: "Search logic", items: ["Signal processing", "Sensor fusion", "Search map", "Next probe"] },
  { title: "Infrastructure", items: ["Hosting", "Logging", "Deployment", "Serial link"] },
  { title: "Validation", items: ["Test environment", "Controlled rubble", "Metrics", "Experiments"] },
];

const STEPS = [
  "Software simulation",
  "Sensor bench testing",
  "Robot chassis integration",
  "Knock mechanism",
  "Acoustic and vibration experiments",
  "Adaptive search validation",
  "Optional cloud model",
  "Hosted demo",
  "Controlled rubble demonstration",
  "Hackathon demonstration",
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
          RubbleEcho is a search-and-rescue rover project. The robot is meant to move through debris, stop, knock, and use the vibration and sound that come back to decide where to look next. This software is the mission dashboard and the bench test for that rover.
        </p>
        <p className="mt-3 max-w-3xl text-[14px] leading-6 text-muted">
          Developed by McNeeseNexus. This software is a simulation prototype. Outputs are estimated and are not validated life-safety measurements.
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
        <h2 className="text-[11px] uppercase tracking-[0.16em] text-muted">Next steps</h2>
        <ol className="mt-4 grid gap-2 sm:grid-cols-2">
          {STEPS.map((step, index) => (
            <li key={step} className="flex gap-3 text-[14px]">
              <span className="num text-muted">{String(index + 1).padStart(2, "0")}</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
