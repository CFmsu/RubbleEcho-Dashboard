import { heatColor } from "../../utils/color";
import type { CandidateLocation, ProbePoint, RobotState } from "../../types/mission";

export function SearchMap({
  grid,
  robot,
  probes,
  candidate,
  groundTruth,
}: {
  grid: number[][];
  robot: RobotState | null;
  probes: ProbePoint[];
  candidate: CandidateLocation | null;
  groundTruth?: { x: number; y: number } | null;
}) {
  const height = grid.length || 12;
  const width = grid[0]?.length || 12;
  const cellCount = width * height;
  const sy = (y: number) => height - y;

  const heading = ((robot?.heading ?? 0) * Math.PI) / 180;
  const fx = Math.cos(heading);
  const fy = Math.sin(heading);
  const rx = robot?.x ?? 1;
  const ry = robot?.y ?? 1;

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#edf1f5]">
      <svg
        viewBox={`-0.85 -0.45 ${width + 1.45} ${height + 1.05}`}
        className="min-h-0 w-full flex-1"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Search map"
      >
        <rect x={0} y={0} width={width} height={height} fill="#e2e8ef" />
        {grid.map((row, iy) =>
          row.map((value, ix) => (
            <rect
              key={`${ix}-${iy}`}
              x={ix + 0.045}
              y={sy(iy + 1) + 0.045}
              width={0.91}
              height={0.91}
              fill={heatColor(value, cellCount)}
              stroke="#c5ced8"
              strokeWidth={0.02}
            />
          )),
        )}
        {robot && robot.trail.length > 1 ? (
          <polyline
            fill="none"
            stroke="rgba(18,24,32,0.5)"
            strokeWidth={0.05}
            points={robot.trail.map(([x, y]) => `${x},${sy(y)}`).join(" ")}
          />
        ) : null}
        {probes.map((probe) => (
          <g key={probe.id}>
            <rect
              x={probe.x - 0.12}
              y={sy(probe.y) - 0.12}
              width={0.24}
              height={0.24}
              fill={probe.is_confirmation ? "#c1121f" : "#121820"}
              opacity={0.92}
            />
          </g>
        ))}
        {robot?.current_target_x != null && robot.current_target_y != null ? (
          <circle
            cx={robot.current_target_x}
            cy={sy(robot.current_target_y)}
            r={0.34}
            fill="none"
            stroke="#e85d04"
            strokeWidth={0.05}
            strokeDasharray="0.12 0.08"
          />
        ) : null}
        <circle cx={rx} cy={sy(ry)} r={0.18} fill="#e85d04" />
        <line x1={rx} y1={sy(ry)} x2={rx + fx * 0.48} y2={sy(ry) - fy * 0.48} stroke="#121820" strokeWidth={0.08} />
        {candidate ? (
          <g>
            <circle cx={candidate.x} cy={sy(candidate.y)} r={0.42} fill="none" stroke="#c1121f" strokeWidth={0.06} />
            <path
              d={`M ${candidate.x} ${sy(candidate.y) - 0.22} L ${candidate.x + 0.22} ${sy(candidate.y)} L ${candidate.x} ${sy(candidate.y) + 0.22} L ${candidate.x - 0.22} ${sy(candidate.y)} Z`}
              fill="#c1121f"
            />
          </g>
        ) : null}
        {groundTruth ? (
          <g>
            <circle cx={groundTruth.x} cy={sy(groundTruth.y)} r={0.28} fill="none" stroke="#1b7a4a" strokeWidth={0.05} />
            <path
              d={`M ${groundTruth.x - 0.16} ${sy(groundTruth.y) - 0.16} L ${groundTruth.x + 0.16} ${sy(groundTruth.y) + 0.16} M ${groundTruth.x + 0.16} ${sy(groundTruth.y) - 0.16} L ${groundTruth.x - 0.16} ${sy(groundTruth.y) + 0.16}`}
              stroke="#1b7a4a"
              strokeWidth={0.05}
            />
          </g>
        ) : null}
        {Array.from({ length: width }, (_, index) => (
          <text key={`x-${index}`} x={index + 0.5} y={height + 0.42} textAnchor="middle" fill="#4a5565" fontSize={0.42}>
            {index + 1}
          </text>
        ))}
        {Array.from({ length: height }, (_, index) => (
          <text key={`y-${index}`} x={-0.28} y={sy(index + 0.5) + 0.14} textAnchor="end" fill="#4a5565" fontSize={0.42}>
            {index + 1}
          </text>
        ))}
      </svg>
      <div className="flex shrink-0 items-center gap-2 px-4 py-2 text-sm text-muted">
        <span>Quiet</span>
        <span
          className="h-2 w-28"
          style={{ background: "linear-gradient(90deg, #d5dde6, #6f9cc8 32%, #e0a84a 68%, #c1121f)" }}
        />
        <span>Hot spot</span>
      </div>
    </div>
  );
}
