const steps = [
  {
    number: '01',
    title: 'Browser',
    description: 'A visitor opens the RubbleEcho dashboard.',
  },
  {
    number: '02',
    title: 'React page',
    description: 'The frontend displays the mission, map, probes, and confidence estimates.',
  },
  {
    number: '03',
    title: 'REST and WebSocket',
    description: 'REST requests control missions and retrieve information. A WebSocket streams telemetry.',
  },
  {
    number: '04',
    title: 'FastAPI backend',
    description: 'The Python API handles requests and manages the simulation.',
  },
  {
    number: '05',
    title: 'Simulated search',
    description: 'The backend generates simulated probe locations, events, and confidence estimates.',
  },
]

function HowItWorks() {
  return (
    <section className="space-y-8">
      <div>
        <h2 className="mb-4 text-3xl font-bold">How RubbleEcho Works</h2>
        <p className="max-w-3xl text-slate-600">
          RubbleEcho is a website demonstration of a search-and-rescue rover
          concept. The current system simulates a mission; it does not control
          a physical rover or collect real field measurements.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {steps.map((step) => (
          <article
            key={step.number}
            className="rounded-xl bg-white p-6 shadow-sm"
          >
            <span className="text-sm font-bold text-blue-600">
              STEP {step.number}
            </span>
            <h3 className="mt-3 text-xl font-semibold">{step.title}</h3>
            <p className="mt-3 text-slate-600">{step.description}</p>
          </article>
        ))}
      </div>

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-6">
        <h3 className="mb-3 text-xl font-semibold text-blue-900">
          What the Dashboard Receives
        </h3>
        <p className="text-blue-900">
          The hidden source stays on the server. The browser receives probe
          locations and confidence estimates, not the hidden source coordinates.
        </p>
      </div>

      <div>
        <h3 className="mb-4 text-2xl font-semibold">Now and Later</h3>
        <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
          <table className="w-full border-collapse text-left">
            <thead className="bg-slate-200">
              <tr>
                <th className="p-4">Part</th>
                <th className="p-4">Now</th>
                <th className="p-4">Possible future version</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t">
                <td className="p-4 font-medium">Movement</td>
                <td className="p-4">Simulated; not connected</td>
                <td className="p-4">A real rover chassis</td>
              </tr>
              <tr className="border-t">
                <td className="p-4 font-medium">Knocker</td>
                <td className="p-4">Simulated; not connected</td>
                <td className="p-4">A physical knocking mechanism</td>
              </tr>
              <tr className="border-t">
                <td className="p-4 font-medium">Microphone</td>
                <td className="p-4">Not connected</td>
                <td className="p-4">A microphone for sound measurements</td>
              </tr>
              <tr className="border-t">
                <td className="p-4 font-medium">Vibration sensor</td>
                <td className="p-4">Not connected</td>
                <td className="p-4">A sensor for vibration measurements</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-sm text-slate-600">
        RubbleEcho is a simulation prototype. It does not locate real people
        and must not be used for a rescue decision.
      </p>
    </section>
  )
}

export default HowItWorks