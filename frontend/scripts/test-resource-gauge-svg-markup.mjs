import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDir = dirname(dirname(fileURLToPath(import.meta.url)))
const file = readFileSync(
  join(frontendDir, 'src', 'views', 'dashboard', 'components', 'ResourceGauges.vue'),
  'utf8',
)

assert.match(file, /<path class="gauge-track"[^>]*fill="none"/)
assert.match(file, /<path class="gauge-track"[^>]*stroke="#f1f3f5"/)
assert.match(file, /<path class="gauge-progress"[\s\S]*fill="none"/)
assert.match(file, /<path class="gauge-progress"[\s\S]*stroke-width="10"/)
assert.match(file, /<path class="gauge-progress"[\s\S]*stroke-linecap="round"/)

console.log('resource gauge svg markup ok')
