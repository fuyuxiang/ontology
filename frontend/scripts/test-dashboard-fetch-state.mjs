import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontendDir = dirname(dirname(fileURLToPath(import.meta.url)))
const outDir = join(frontendDir, 'node_modules', '.tmp', 'dashboard-fetch-state-test')
rmSync(outDir, { recursive: true, force: true })
mkdirSync(outDir, { recursive: true })

execFileSync(
  process.execPath,
  [
    join(frontendDir, 'node_modules', 'typescript', 'bin', 'tsc'),
    'src/views/dashboard/dashboardFetchState.ts',
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

const { mergeDashboardFetchState } = await import(
  pathToFileURL(join(outDir, 'views', 'dashboard', 'dashboardFetchState.js')).href
)

const previous = {
  resources: { cpu_percent: 10, memory_percent: 20, memory_used_gb: 1, memory_total_gb: 2, disk_percent: 30, disk_used_gb: 3, disk_total_gb: 4 },
  services: [{ name: 'API', status: 'healthy', response_ms: 10 }],
  alerts: [{ id: 1, level: 'warning', service_name: 'API', message: 'slow', resolved: false, created_at: '2026-06-04T00:00:00', resolved_at: null }],
  llmStats: { total_24h: 1, by_module: {} },
  ontologyStats: { total_entities: 2, by_type: { Customer: 2 } },
  agentActivity: { total_agents: 3, published_agents: 2, total_skills: 4 },
  platformStats: { total_datasources: 5, total_rules: 6, total_pipelines: 7 },
}

const result = mergeDashboardFetchState(previous, {
  resources: { status: 'fulfilled', value: { cpu_percent: 11, memory_percent: 21, memory_used_gb: 1.1, memory_total_gb: 2, disk_percent: 31, disk_used_gb: 3.1, disk_total_gb: 4 } },
  services: { status: 'rejected', reason: new Error('services down') },
  alerts: { status: 'fulfilled', value: [] },
  llmStats: { status: 'fulfilled', value: { total_24h: 0, by_module: {} } },
  ontologyStats: { status: 'rejected', reason: new Error('ontology failed') },
  agentActivity: { status: 'fulfilled', value: { total_agents: 4, published_agents: 3, total_skills: 5 } },
  platformStats: { status: 'rejected', reason: new Error('stats failed') },
})

assert.deepEqual(result.next.resources, { cpu_percent: 11, memory_percent: 21, memory_used_gb: 1.1, memory_total_gb: 2, disk_percent: 31, disk_used_gb: 3.1, disk_total_gb: 4 })
assert.deepEqual(result.next.services, previous.services)
assert.deepEqual(result.next.alerts, [])
assert.deepEqual(result.next.llmStats, { total_24h: 0, by_module: {} })
assert.deepEqual(result.next.ontologyStats, previous.ontologyStats)
assert.deepEqual(result.next.agentActivity, { total_agents: 4, published_agents: 3, total_skills: 5 })
assert.deepEqual(result.next.platformStats, previous.platformStats)
assert.deepEqual(result.failedKeys, ['services', 'ontologyStats', 'platformStats'])

console.log('dashboard fetch state merge ok')
