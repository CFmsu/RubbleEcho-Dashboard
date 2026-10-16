import { Area, AreaChart, ResponsiveContainer, YAxis } from "recharts";

export function WaveformChart({
  samples,
  stroke,
  empty,
  className = "h-[72px]",
}: {
  samples: number[] | undefined;
  stroke: string;
  empty: string;
  className?: string;
}) {
  const data = (samples && samples.length > 0 ? samples : [0, 0, 0, 0]).map((value, index) => ({
    i: index,
    v: value,
  }));
  const waiting = !samples || samples.length === 0;
  return (
    <div className={`relative ${className}`}>
      {waiting ? (
        <div className="absolute inset-0 z-10 flex items-center justify-center text-sm text-muted">{empty}</div>
      ) : null}
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
          <YAxis hide domain={[-1, 1]} />
          <Area
            type="monotone"
            dataKey="v"
            stroke={stroke}
            fill={stroke}
            fillOpacity={0.12}
            strokeWidth={1.4}
            isAnimationActive={false}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
