
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
      <div className="mb-8 rounded-xl bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-xl font-semibold">
        The Nine-Step Search Process
      </h3>

     <ol className="list-decimal space-y-2 pl-6 text-slate-600">
      <li>Explore the search area.</li>
      <li>Stop at a selected location.</li>
      <li>Knock to prompt a possible response.</li>
      <li>Listen for sound or vibration.</li>
      <li>Score the simulated observation.</li>
      <li>Update the map with the result.</li>
      <li>Pick the next location to check.</li>
      <li>Repeat the search process.</li>
      <li>Mark a promising spot for a person to verify.</li>
  </ol>
  </div>

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
      <div className="mt-8 rounded-xl border border-amber-300 bg-amber-50 p-6">
  <h3 className="mb-4 text-xl font-semibold">
    Hardware Later
  </h3>

  <ul className="space-y-2 text-slate-700">
    <li>Movement: not connected.</li>
    <li>Knocker: not connected.</li>
    <li>Microphone: not connected.</li>
    <li>Vibration sensor: not connected.</li>
  </ul>
</div>
    </section>
  )
}

export default About
