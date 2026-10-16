export function formatRuntime(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(whole / 60);
  const remain = whole % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remain).padStart(2, "0")}`;
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatFixed(value: number, digits = 2): string {
  return value.toFixed(digits);
}

export function confidenceBand(value: number): "LOW" | "INVESTIGATE" | "HIGH" | "CONFIRM" {
  const pct = value * 100;
  if (pct >= 80) return "CONFIRM";
  if (pct >= 60) return "HIGH";
  if (pct >= 30) return "INVESTIGATE";
  return "LOW";
}
