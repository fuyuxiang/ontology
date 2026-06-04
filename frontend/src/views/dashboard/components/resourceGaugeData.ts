export function clampPercent(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, value))
}

export function gaugeColor(value: number): string {
  const percent = clampPercent(value)
  if (percent < 60) return '#20c997'
  if (percent < 85) return '#f59f00'
  return '#fa5252'
}

export function gaugeDashArray(value: number): string {
  const percent = clampPercent(value)
  return `${(percent * 1.1).toFixed(0)} 200`
}
