// Interactive or replayable browser acceptance. No API bypass or business DB seed.
// PLAYWRIGHT_MODULE=/absolute/playwright-core/index.mjs CHROMIUM_EXECUTABLE=/path/chrome
// node tests/review-browser.mjs [steps.json]
import { pathToFileURL } from 'node:url'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { createInterface } from 'node:readline'
import path from 'node:path'

const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE || ''))
const evidence = path.resolve('../docs/review/evidence/browser')
await mkdir(evidence, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await context.newPage()
const steps = [], network = [], errors = []
function redact(value) {
  if (Array.isArray(value)) return value.map(redact)
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, val]) => [key,
    /password|secret|token|api_key|sso_code/i.test(key) ? '[REDACTED]' : redact(val)]))
  return value
}
page.on('pageerror', error => errors.push(error.message))
page.on('response', async response => {
  if (!response.url().includes('/api/')) return
  const request = response.request()
  let body
  try { body = redact(await response.json()) } catch { body = (await response.text().catch(() => '')).slice(0, 2000) }
  let input
  try { input = redact(request.postDataJSON()) } catch { input = '[non-JSON input]' }
  network.push({ method: request.method(), url: response.url().replace(/(sso_code|code|state)=[^&]+/g, '$1=[REDACTED]'),
    status: response.status(), input, body })
})
function target(command) {
  command = command.target || command
  let locator = command.css ? page.locator(command.css) : command.placeholder ? page.getByPlaceholder(command.placeholder, { exact: true })
    : command.role ? page.getByRole(command.role, { name: command.name, exact: command.exact !== false })
      : page.getByText(command.text, { exact: command.exact !== false })
  if (command.nth !== undefined) locator = locator.nth(command.nth)
  return locator
}
async function save() {
  await writeFile(path.join(evidence, 'steps.json'), JSON.stringify(steps, null, 2))
  await writeFile(path.join(evidence, 'network.json'), JSON.stringify(network, null, 2))
  await writeFile(path.join(evidence, 'page-errors.json'), JSON.stringify(errors, null, 2))
}
async function execute(command) {
  const action = command.action
  if (action === 'goto') await page.goto(command.url)
  else if (action === 'click') await target(command).click()
  else if (action === 'fill') await target(command).fill(command.valueEnv ? process.env[command.valueEnv] : command.value)
  else if (action === 'select') await target(command).selectOption(command.value)
  else if (action === 'check') await target(command).setChecked(command.value)
  else if (action === 'press') await target(command).press(command.key)
  else if (action === 'reload') await page.reload()
  else if (action === 'viewport') await page.setViewportSize({ width: command.width, height: command.height })
  else if (action === 'wait') await target(command).waitFor({ state: command.state || 'visible' })
  else if (action === 'screenshot') await page.screenshot({ path: path.join(evidence, command.name + '.png'), fullPage: true })
  else if (action !== 'read') throw new Error('Unsupported browser action: ' + action)
  steps.push(action === 'fill' && /password/i.test(command.css || command.placeholder || JSON.stringify(command.target || {})) ? { ...command, value: undefined, valueEnv: command.valueEnv || 'REVIEW_PASSWORD' } : command)
  await save()
  return { url: page.url().replace(/(sso_code|code|state)=[^&]+/g, '$1=[REDACTED]'),
    text: (await page.locator('body').innerText()).slice(0, 12000),
    controls: await page.locator('input,select,textarea,button').evaluateAll(nodes => nodes.filter(n => n.getClientRects().length).map(n => ({ tag: n.tagName,
      type: n.type, placeholder: n.placeholder, text: n.tagName === 'BUTTON' ? n.textContent.trim() : undefined,
      title: n.title, value: n.type === 'password' ? '[REDACTED]' : n.value, disabled: n.disabled }))) }
}
try {
  if (process.argv[2]) {
    for (const command of JSON.parse(await readFile(process.argv[2], 'utf8'))) {
      await execute(command)
      console.log(JSON.stringify({ action: command.action, outcome: 'passed' }))
    }
  } else {
    console.log('BROWSER_READY')
    for await (const line of createInterface({ input: process.stdin, terminal: false })) {
      try { console.log(JSON.stringify(await execute(JSON.parse(line)))) }
      catch (error) { console.log(JSON.stringify({ error: error.message })); await save() }
    }
  }
} finally { await save(); await browser.close() }
