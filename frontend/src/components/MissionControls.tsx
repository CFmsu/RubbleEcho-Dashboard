
import { useState } from 'react'

type Scenario = 'earthquake' | 'flood' | 'collapse'

function MissionControls() {
  const [scenario, setScenario] = useState<Scenario>('collapse')

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-xl font-semibold">
        Mission Controls
      </h3>

      <div className="mb-5">
        <label
          htmlFor="scenario"
          className="mb-2 block font-medium text-slate-700"
        >
          Select Scenario
        </label>

        <select
          id="scenario"
          value={scenario}
          onChange={(e) =>
            setScenario(e.target.value as Scenario)
          }
          className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3"
        >
          <option value="earthquake">Earthquake</option>
          <option value="flood">Flood</option>
          <option value="collapse">Collapse</option>
        </select>
      </div>

      <div className="flex flex-wrap gap-3">
        {['Demo', 'Start', 'Pause', 'Step', 'Reset'].map(
          (action) => (
            <button
              key={action}
              type="button"
              onClick={() =>
                console.log(`${action} clicked`, scenario)
              }
              className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700"
            >
              {action}
            </button>
          )
        )}
      </div>

      <p className="mt-4 text-sm text-slate-500">
        Controls are not connected to the backend yet.
      </p>
    </div>
  )
}

export default MissionControls
