import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontendDir = dirname(dirname(fileURLToPath(import.meta.url)))
const outDir = join(frontendDir, 'node_modules', '.tmp', 'response-time-chart-test')
rmSync(outDir, { recursive: true, force: true })
mkdirSync(outDir, { recursive: true })

execFileSync(
  process.execPath,
  [
    join(frontendDir, 'node_modules', 'typescript', 'bin', 'tsc'),
    'src/views/dashboard/components/responseTimeChartData.ts',
    'src/api/monitor.ts',
    'src/api/client.ts',
    '--target',
    'ES2022',
    '--module',
    'ES2022',
    '--moduleResolution',
    'bundler',
    '--ignoreConfig',
    '--types',
    'vite/client',
    '--skipLibCheck',
    '--outDir',
    outDir,
  ],
  { cwd: frontendDir, stdio: 'inherit' },
)

writeFileSync(join(outDir, 'package.json'), '{"type":"module"}')

const { buildResponseTimeChartData } = await import(
  pathToFileURL(join(outDir, 'views', 'dashboard', 'components', 'responseTimeChartData.js')).href
)

const result = buildResponseTimeChartData([
  { service_name: '后端API', response_ms: 100, status: 'healthy', collected_at: '2026-06-04T00:00:00' },
  { service_name: '数据库', response_ms: 20, status: 'healthy', collected_at: '2026-06-04T00:00:00' },
  { service_name: '后端API', response_ms: 120, status: 'healthy', collected_at: '2026-06-04T00:00:30' },
  { service_name: '后端API', response_ms: 90, status: 'healthy', collected_at: '2026-06-04T00:01:00' },
  { service_name: '数据库', response_ms: 25, status: 'healthy', collected_at: '2026-06-04T00:01:00' },
])

assert.deepEqual(result.series, [
  {
    name: '后端API',
    points: [
      ['2026-06-04T00:00:00', 100],
      ['2026-06-04T00:00:30', 120],
      ['2026-06-04T00:01:00', 90],
    ],
  },
  {
    name: '数据库',
    points: [
      ['2026-06-04T00:00:00', 20],
      ['2026-06-04T00:01:00', 25],
    ],
  },
])

console.log('response time chart data alignment ok')
