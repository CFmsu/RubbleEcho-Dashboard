
import { useState } from 'react'
import RoverMap from './components/RoverMap'
import MissionStatus from './components/MissionStatus'
import MissionControls from './components/MissionControls'
import HowItWorks from './components/HowItWorks'
import About from './components/About'
import { useTelemetry } from './hooks/useTelemetry'

type Page = 'live' | 'how' | 'about'

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('live')
  const { telemetry, connectionStatus } = useTelemetry()

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="bg-slate-900 text-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-5">
          <h1 className="text-2xl font-bold">
            RubbleEcho
          </h1>

          {/* Navigation */}
          <nav aria-label="Main navigation" className="flex flex-wrap gap-3">
            <button
              onClick={() => setCurrentPage('live')}
              className={`rounded-lg px-4 py-2 ${
                currentPage === 'live'
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-slate-700'
              }`}
            >
              Live Run
            </button>

            <button
              onClick={() => setCurrentPage('how')}
              className={`rounded-lg px-4 py-2 ${
                currentPage === 'how'
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-slate-700'
              }`}
            >
              How It Works
            </button>

            <button
              onClick={() => setCurrentPage('about')}
              className={`rounded-lg px-4 py-2 ${
                currentPage === 'about'
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-slate-700'
              }`}
            >
              About
            </button>
          </nav>
        </div>
      </header>

      {/* Page content */}
      <main className="mx-auto max-w-6xl px-6 py-10">
        
        {currentPage === 'live' && (
          <section>
            <h2 className="mb-4 text-3xl font-bold">
              Live Run
            </h2>

            <p className="mb-6 text-slate-600">
              Watch the RubbleEcho rover simulation.
            </p>

            {/* Backend Connection Status */}
            <div className="mb-6">
              <span
                className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 font-medium ${
                  connectionStatus === 'connected'
                    ? 'bg-green-100 text-green-700'
                    : connectionStatus === 'connecting'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                }`}
              >
                <span
                  className={`h-3 w-3 rounded-full ${
                    connectionStatus === 'connected'
                      ? 'bg-green-500'
                      : connectionStatus === 'connecting'
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                  }`}
                />

                {connectionStatus === 'connected'
                  ? 'Telemetry Connected'
                  : connectionStatus === 'connecting'
                    ? 'Connecting to Telemetry...'
                    : 'Telemetry Disconnected'}
              </span>
            </div>


            {/* Rover Map and Mission Status */}
            <div className="mt-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
              <RoverMap
                robot={telemetry.robot}
                probes={telemetry.probes}
              />

              <MissionStatus
                confidence={telemetry.mission.confidence}
                phase={telemetry.mission.phase}
                events={telemetry.events}
              />
            </div>

            {/* Mission Controls */}
            <div className="mt-6">
              <MissionControls />
            </div>

          </section>
        )}

        {currentPage === 'how' && <HowItWorks />}

        {currentPage === 'about' && <About />}
      </main>
    </div>
  )
}

export default App
