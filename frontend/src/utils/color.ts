const STOPS: Array<[number, number, number]> = [
  [213, 221, 230],
  [111, 156, 200],
  [224, 168, 74],
  [232, 93, 4],
  [193, 18, 31],
];

export function heatColor(value: number, cellCount: number): string {
  const uniform = 1 / Math.max(cellCount, 1);
  const ratio = value / uniform;
  const t = Math.max(0, Math.min(1, Math.log(Math.max(ratio, 1)) / Math.log(8)));
  const scaled = t * (STOPS.length - 1);
  const index = Math.min(STOPS.length - 2, Math.floor(scaled));
  const blend = scaled - index;
  const start = STOPS[index];
  const end = STOPS[index + 1];
  const red = Math.round(start[0] + (end[0] - start[0]) * blend);
  const green = Math.round(start[1] + (end[1] - start[1]) * blend);
  const blue = Math.round(start[2] + (end[2] - start[2]) * blend);
  return `rgb(${red}, ${green}, ${blue})`;
}
