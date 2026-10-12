import { usePlatformConfigStore } from '../store/platformConfig'

/** Backend naive datetimes represent UTC, never the browser's local timezone. */
export function parsePlatformTimestamp(value: string | Date): Date {
  if (value instanceof Date) return value
  const normalized = value.trim().replace(' ', 'T')
  const iso = /^\d{4}-\d{2}-\d{2}$/.test(normalized) ? `${normalized}T00:00:00Z`
    : /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(normalized) && !/(Z|[+-]\d{2}:?\d{2})$/i.test(normalized) ? `${normalized}Z` : normalized
  return new Date(iso)
}

export function formatPlatformDateTime(value?: string | Date | null, options: Intl.DateTimeFormatOptions = {}): string {
  if (!value) return '—'
  const date = parsePlatformTimestamp(value)
  if (Number.isNaN(date.getTime())) return String(value)
  const platform = usePlatformConfigStore()
  return new Intl.DateTimeFormat(platform.language, {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false, timeZoneName: 'short', ...options, timeZone: platform.timezone,
  }).format(date)
}

export function formatPlatformTime(value?: string | Date | null, options: Intl.DateTimeFormatOptions = {}): string {
  return formatPlatformDateTime(value, { year: undefined, month: undefined, day: undefined, ...options })
}
