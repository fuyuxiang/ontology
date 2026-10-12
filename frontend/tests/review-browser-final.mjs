// Interactive or replayable browser acceptance. No API bypass or business DB seed.
// PLAYWRIGHT_MODULE=/absolute/playwright-core/index.mjs CHROMIUM_EXECUTABLE=/path/chrome
// node tests/review-browser-final.mjs [steps.json]
import { pathToFileURL } from 'node:url'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { createInterface } from 'node:readline'
import path from 'node:path'

const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE || ''))
const evidence = path.resolve(process.env.REVIEW_EVIDENCE_DIR || '../docs/review/evidence/browser-final')
await mkdir(evidence, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await context.newPage()
async function prior(name) {try{return JSON.parse(await readFile(path.join(evidence,name),'utf8'))}catch{return []}}
const steps=process.argv[2]?[]:await prior('steps.json'),network=process.argv[2]?[]:await prior('network.json'),errors=process.argv[2]?[]:await prior('page-errors.json')
const suffix=Date.now().toString(36)
const variables={FRONTEND_ORIGIN:process.env.REVIEW_FRONTEND_ORIGIN||'http://127.0.0.1:5179',REVIEW_CODE:process.env.REVIEW_CODE||`review_${suffix}`,REVIEW_NAME:process.env.REVIEW_NAME||`设备检修复验 ${suffix}`,REVIEW_CONN_NAME:process.env.REVIEW_CONN_NAME||`devices_${suffix}`,REVIEW_ASSET_NAME:process.env.REVIEW_ASSET_NAME||`设备实例_${suffix}`,REVIEW_RECEIPT_URL:process.env.REVIEW_RECEIPT_URL||'http://127.0.0.1:5056/fixture/actions'}
function resolve(value){if(typeof value==='string')return value.replace(/\$\{([A-Z_]+)\}/g,(_,key)=>{if(variables[key]===undefined)throw new Error('Unset replay variable: '+key);return String(variables[key])});if(Array.isArray(value))return value.map(resolve);if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,resolve(v)]));return value}
page.on('dialog',async dialog=>{steps.push({action:'native-dialog',type:dialog.type(),message:dialog.message(),decision:process.env.REVIEW_ACCEPT_DIALOGS==='true'?'accept':'dismiss'});if(process.env.REVIEW_ACCEPT_DIALOGS==='true')await dialog.accept();else await dialog.dismiss()})
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
  const recorded=command;command=resolve(command)
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
  else if (action === 'assert') { if (!(await target(command).isVisible())) throw new Error('Expected visible: '+JSON.stringify(command.target || command));if(command.contains!==undefined&&!(await target(command).innerText()).includes(command.contains))throw new Error('Missing expected content: '+command.contains) }
  else if(action==='capture'){
    const deadline=Date.now()+30000;let value
    while(Date.now()<deadline){const matches=(expected,actual)=>Object.entries(expected||{}).every(([key,value])=>key.split('.').reduce((current,part)=>current?.[part],actual)===value);const found=network.findLast(row=>row.method===(command.method||'POST')&&new URL(row.url).pathname.endsWith(command.urlEndsWith)&&row.status<400&&matches(command.inputEquals,row.input)&&matches(command.bodyEquals,row.body));value=command.field.split('.').reduce((current,key)=>current?.[key],found?.body);if(value!==undefined)break;await new Promise(done=>setTimeout(done,50))}
    if(value===undefined)throw new Error('No observed successful response field: '+command.field)
    variables[command.name]=value;await writeFile(path.join(evidence,'captured-ids.json'),JSON.stringify(variables,null,2))
  }
  else if (action === 'screenshot') await page.screenshot({ path: path.join(evidence, command.name + '.png'), fullPage: true, animations:'disabled' })
  else if (action !== 'read') throw new Error('Unsupported browser action: ' + action)
  steps.push(action === 'fill' && /password/i.test(command.css || command.placeholder || JSON.stringify(command.target || {})) ? { ...command, value: undefined, valueEnv: command.valueEnv || 'REVIEW_PASSWORD' } : recorded)
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
