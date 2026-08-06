/**
 * Generate a RFC4122 v4 UUID.
 *
 * `crypto.randomUUID()` and `crypto.getRandomValues()` are only exposed in a
 * secure context (HTTPS or localhost). When the app is served over plain HTTP
 * from an IP address, they are unavailable, so fall back progressively.
 */
export function randomUUID(): string {
  const c: Crypto | undefined = globalThis.crypto

  if (typeof c?.randomUUID === 'function') {
    return c.randomUUID()
  }

  if (typeof c?.getRandomValues === 'function') {
    const bytes = c.getRandomValues(new Uint8Array(16))
    bytes[6] = (bytes[6] & 0x0f) | 0x40
    bytes[8] = (bytes[8] & 0x3f) | 0x80
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
  }

  // Last resort: Math.random based. Not cryptographically strong, but these ids
  // are only used as client-side session/draft keys.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (ch) => {
    const r = (Math.random() * 16) | 0
    const v = ch === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}
