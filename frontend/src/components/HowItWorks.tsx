
const steps = [
  {
    number: '01',
    title: 'Move',
    description:
      'The rover navigates through a controlled test environment.',
  },
  {
    number: '02',
    title: 'Knock',
    description:
      'The rover performs a controlled knock on a surface.',
  },
  {
    number: '03',
    title: 'Listen',
    description:
      'Sensors collect acoustic or vibration information.',
  },
  {
    number: '04',
    title: 'Analyze',
    description:
      'The collected signals are processed to evaluate the measurement.',
  },
  {
    number: '05',
    title: 'Decide',
    description:
      'The system determines where the rover should measure next.',
  },
  {
    number: '06',
    title: 'Repeat',
    description:
      'The rover continues the measurement process.',
  },
]

function HowItWorks() {
  return (
    <section>
      <h2 className="mb-4 text-3xl font-bold">
        How RubbleEcho Works
      </h2>

      <p className="mb-8 text-slate-600">
        RubbleEcho is a prototype rover designed to explore
        a controlled environment, collect measurements,
        and support decisions about where to measure next.
      </p>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {steps.map((step) => (
          <div
            key={step.number}
            className="rounded-xl bg-white p-6 shadow-sm"
          >
            <span className="text-sm font-bold text-blue-600">
              STEP {step.number}
            </span>

            <h3 className="mt-3 text-xl font-semibold">
              {step.title}
            </h3>

            <p className="mt-3 text-slate-600">
              {step.description}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-8 rounded-xl border border-blue-200 bg-blue-50 p-6">
        <h3 className="mb-2 text-lg font-semibold text-blue-900">
          Research Prototype
        </h3>

        <p className="text-blue-800">
          RubbleEcho is a research demonstration.
          Its simulated outputs should not be interpreted
          as verified field measurements or safety assessments.
        </p>
      </div>
    </section>
  )
}

export default HowItWorks
