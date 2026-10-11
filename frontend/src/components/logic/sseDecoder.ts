/** Buffer SSE data lines across arbitrary network and UTF-8 chunk boundaries. */
export function createSseDecoder(onData: (data: string) => void) {
  const decoder = new TextDecoder()
  let pending = ''

  function drain(final = false) {
    let newline = pending.indexOf('\n')
    while (newline !== -1) {
      const line = pending.slice(0, newline).replace(/\r$/, '')
      pending = pending.slice(newline + 1)
      if (line.startsWith('data:')) onData(line.slice(5).trimStart())
      newline = pending.indexOf('\n')
    }
    if (final && pending) {
      const line = pending.replace(/\r$/, '')
      pending = ''
      if (line.startsWith('data:')) onData(line.slice(5).trimStart())
    }
  }

  return {
    push(chunk: Uint8Array) {
      pending += decoder.decode(chunk, { stream: true })
      drain()
    },
    finish() {
      pending += decoder.decode()
      drain(true)
    },
  }
}
