import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontendDir = dirname(dirname(fileURLToPath(import.meta.url)))
const outDir = join(frontendDir, 'node_modules', '.tmp', 'resource-gauge-data-test')
rmSync(outDir, { recursive: true, force: true })
mkdirSync(outDir, { recursive: true })

execFileSync(
  process.execPath,
  [
    join(frontendDir, 'node_modules', 'typescript', 'bin', 'tsc'),
    'src/views/dashboard/components/resourceGaugeData.ts',
    '--target',
    'ES2022',
    '--module',
    'ES2022',
    '--moduleResolution',
    'bundler',
    '--ignoreConfig',
    '--skipLibCheck',
    '--outDir',
    outDir,
  ],
  { cwd: frontendDir, stdio: 'inherit' },
)

writeFileSync(join(outDir, 'package.json'), '{"type":"module"}')

const { clampPercent, gaugeColor, gaugeDashArray } = await import(
  pathToFileURL(join(outDir, 'resourceGaugeData.js')).href
)

assert.equal(clampPercent(-1), 0)
assert.equal(clampPercent(37.6), 37.6)
assert.equal(clampPercent(140), 100)
assert.equal(clampPercent(Number.NaN), 0)

assert.equal(gaugeColor(59.9), '#20c997')
assert.equal(gaugeColor(60), '#f59f00')
assert.equal(gaugeColor(85), '#fa5252')

assert.equal(gaugeDashArray(50), '55 200')
assert.equal(gaugeDashArray(150), '110 200')

console.log('resource gauge data ok')
