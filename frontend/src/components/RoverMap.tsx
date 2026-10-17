
type Position = {
  x: number
  y: number
}

type Probe = Position & {
  id: string
  confidence: number
}

type RoverMapProps = {
  robot: Position
  probes: Probe[]
}

function RoverMap({ robot, probes }: RoverMapProps) {
  const gridSize = 12

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-xl font-semibold">
        Rover Map
      </h3>

      <div
        className="grid aspect-square w-full max-w-lg grid-cols-12 border border-slate-300"
        role="img"
        aria-label={`12 by 12 rover map. Robot at ${robot.x}, ${robot.y}. ${probes.length} probes recorded.`}
      >
        {Array.from({ length: gridSize * gridSize }, (_, index) => {
          const x = index % gridSize
          const y = Math.floor(index / gridSize)

          const isRobot = robot.x === x && robot.y === y
          const probe = probes.find(
            (p) => p.x === x && p.y === y
          )

          return (
            <div
              key={index}
              className="flex aspect-square items-center justify-center border border-slate-200 bg-slate-50"
              title={`Position (${x}, ${y})`}
            >
              {isRobot ? (
                <span
                  className="h-3 w-3 rounded-full bg-blue-600 sm:h-4 sm:w-4"
                  title="Robot"
                />
              ) : probe ? (
                <span
                  className="h-2.5 w-2.5 rounded-full bg-orange-500 sm:h-3 sm:w-3"
                  title={`${probe.id}: ${Math.round(probe.confidence * 100)}%`}
                />
              ) : null}
            </div>
          )
        })}
      </div>

      <div className="mt-4 flex gap-6 text-sm text-slate-600">
        <span>🔵 Robot</span>
        <span>🟠 Probe locations</span>
      </div>
    </div>
  )
}

export default RoverMap
