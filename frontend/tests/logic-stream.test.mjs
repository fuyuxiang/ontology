import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(
  new URL('../src/components/logic/sseDecoder.ts', import.meta.url),
  'utf8',
)
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
}).outputText
const { createSseDecoder } = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`
)

test('AI code SSE preserves JSON and Chinese text across every possible chunk boundary', () => {
  const events = [
    { event: 'chunk', content: '设备🙂' },
    { event: 'chunk', content: '\nresult = {"风险": 90}' },
    { event: 'done', full_code: '设备🙂\nresult = {"风险": 90}' },
  ]
  const bytes = new TextEncoder().encode(
    events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(''),
  )
  for (let split = 1; split < bytes.length; split++) {
    const decoded = []
    const stream = createSseDecoder((data) => decoded.push(JSON.parse(data)))
    stream.push(bytes.slice(0, split))
    stream.push(bytes.slice(split))
    stream.finish()
    assert.deepEqual(decoded, events, `chunk boundary ${split}`)
  }
})

test('AI code SSE supports CRLF, one byte chunks, comments, and final data without newline', () => {
  const decoded = []
  const stream = createSseDecoder((data) => decoded.push(JSON.parse(data)))
  const bytes = new TextEncoder().encode(
    ': heartbeat\r\ndata:{"event":"chunk","content":"中文"}\r\n\r\ndata: {"event":"done","full_code":"中文"}',
  )
  for (const byte of bytes) stream.push(new Uint8Array([byte]))
  stream.finish()
  assert.deepEqual(decoded, [
    { event: 'chunk', content: '中文' },
    { event: 'done', full_code: '中文' },
  ])
})
