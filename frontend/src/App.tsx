
import { useState } from 'react'
import RoverMap from './components/RoverMap'
import MissionStatus from './components/MissionStatus'
import MissionControls from './components/MissionControls'
import HowItWorks from './components/HowItWorks'
import About from './components/About'

type Page = 'live' | 'how' | 'about'

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('live')

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

            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
              Simulated demo. These numbers are not field measurements.
            </div>
            
            {/* Rover Map and Mission Status */}
            <div className="mt-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
              <RoverMap
                robot={{ x: 4, y: 5 }}
                probes={[
                  { id: 'P01', x: 3, y: 4, confidence: 0.22 },
                  { id: 'P02', x: 6, y: 7, confidence: 0.41 },
                ]}
              />

              <MissionStatus
                confidence={0.41}
                phase="listen"
                events={[
                  'Stopped.',
                  'Knocked.',
                  'Listening.',
                ]}
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
