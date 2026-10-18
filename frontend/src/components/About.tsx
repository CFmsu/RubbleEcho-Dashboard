
function About() {
  return (
    <section>
      <h2 className="mb-4 text-3xl font-bold">
        About RubbleEcho
      </h2>

      <p className="mb-8 text-lg text-slate-600">
        RubbleEcho is a Physical AI research prototype
        exploring how a rover can collect acoustic and
        vibration measurements and use those observations
        to guide its next actions.
      </p>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Project Goal */}
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-xl font-semibold">
            Project Goal
          </h3>

          <p className="text-slate-600">
            The goal is to demonstrate a rover that can
            move through a controlled environment,
            perform measurements, and use the collected
            information to select future measurement
            locations.
          </p>
        </div>

        {/* Technology */}
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-xl font-semibold">
            Technology
          </h3>

          <p className="text-slate-600">
            The prototype combines rover movement,
            sensors, signal processing, and
            AI-assisted decision-making.
          </p>
        </div>

        {/* Dashboard */}
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-xl font-semibold">
            Dashboard
          </h3>

          <p className="text-slate-600">
            The dashboard is being developed with
            React, TypeScript, Vite, and Tailwind CSS
            to visualize rover activity and
            simulation information.
          </p>
        </div>

        {/* Project Status */}
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h3 className="mb-3 text-xl font-semibold">
            Project Status
          </h3>

          <p className="text-slate-600">
          RubbleEcho is currently under development.
          The dashboard is integrated with a local simulation
          backend. Live telemetry and mission controls are
          being tested; physical rover hardware integration
          remains future work.
          </p>
        </div>
      </div>

      <p className="mt-8 text-sm text-slate-500">
        RubbleEcho is intended for research and
        demonstration, not operational rescue
        or structural safety decisions.
      </p>
    </section>
  )
}

export default About
