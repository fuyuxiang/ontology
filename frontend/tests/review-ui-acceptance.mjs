// Read actual pages, exercise persisted groups and Agent chat/rejection through UI.
// Requires the fresh API flow and explicit isolated browser/password environment.
import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import path from 'node:path'

const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE))
const evidence = path.resolve('../docs/review/evidence/ui-acceptance')
const fresh = JSON.parse(await readFile('../docs/review/evidence/agd-skills-agent-fresh.json', 'utf8'))
const base = process.env.REVIEW_UI_BASE || 'http://127.0.0.1:5179'
assert(/^http:\/\/127\.0\.0\.1:\d+$/.test(base), 'Only isolated loopback UI is allowed')
await mkdir(evidence, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
page.setDefaultTimeout(15000)
const network = [], errors = [], checks = []
page.on('pageerror', error => errors.push(error.message))
page.on('response', response => {
  if (response.url().includes('/api/')) network.push({ path: new URL(response.url()).pathname, status: response.status() })
})
async function visit(url, expected) {
  await page.goto(base + url)
  await page.getByText(expected, { exact: true }).first().waitFor()
  checks.push({ url, expected, result: 'visible' })
}
async function screenshot(name) {
  await page.screenshot({ path: path.join(evidence, name + '.png'), fullPage: true, animations: 'disabled' })
}
try {
  await page.goto(base + '/login')
  await page.getByLabel('用户名', { exact: true }).fill(process.env.REVIEW_USERNAME || 'admin')
  await page.getByLabel('密码', { exact: true }).fill(process.env.REVIEW_PASSWORD)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.waitForURL('**/dashboard')
  for (const [url, expected] of [
    ['/ontology/list', '本体列表'], ['/data/connections', '数据接入'],
    ['/data/assets', '资产目录'], ['/logic/functions', '逻辑建模'],
    ['/logic/actions', '行动建模'], ['/ontology/publish', '本体发布'],
    ['/service/mcp', '本体服务'], ['/skills', '业务技能'],
    ['/agent/manage', '智能体应用'], ['/ops/config', '系统配置'],
  ]) await visit(url, expected)

  const ontologyCode = process.env.REVIEW_ONTOLOGY_CODE || 'review_browser_final'
  await page.goto(base + '/ontology/list/' + ontologyCode)
  await page.getByRole('button', { name: '分组', exact: false }).click()
  await page.getByRole('heading', { name: '对象分组', exact: true }).waitFor()
  const groupName = '浏览器持久化设备组-' + Date.now()
  await page.getByLabel('分组名称', { exact: true }).fill(groupName)
  await page.locator('.resource-panel fieldset input[type=checkbox]').first().check()
  await Promise.all([page.waitForResponse(r => r.request().method() === 'POST' && /\/ontology\/[^/]+\/groups$/.test(new URL(r.url()).pathname) && r.status() === 201),
    page.getByRole('button', { name: '创建分组', exact: true }).click()])
  await page.getByRole('heading', { name: groupName, exact: true }).waitFor()
  await page.reload()
  await page.getByRole('button', { name: '分组', exact: false }).click()
  await page.getByRole('heading', { name: groupName, exact: true }).waitFor()
  checks.push({ flow: 'CORE-009', operation: 'create group with member, refresh and re-open', groupName, result: 'persisted and visible' })
  await screenshot('persisted-object-group')

  await page.goto(base + '/skills/' + fresh.ids.skill)
  await page.getByRole('tab', { name: '测试与版本', exact: true }).click()
  await page.getByRole('heading', { name: '最近测试记录', exact: true }).waitFor()
  assert((await page.locator('body').innerText()).includes('告警风险与模拟处置'))
  await screenshot('skill-runtime-tests')
  checks.push({ flow: 'G', operation: 'UI reads published Skill and real runtime test history', result: 'visible' })

  await page.goto(base + '/agent/manage/' + fresh.ids.react_agent)
  const chat = page.getByRole('complementary', { name: '智能体对话调试' })
  await chat.getByRole('button', { name: '新会话', exact: true }).click()
  await chat.getByRole('textbox', { name: '调试问题', exact: true }).fill('计算设备风险')
  await chat.getByRole('button', { name: '发送', exact: true }).click()
  await chat.locator('.aw-bubble-assistant .aw-markdown').filter({ hasText: '设备风险较高' }).waitFor()
  await chat.getByRole('button', { name: '发送', exact: true }).waitFor()
  await screenshot('agent-real-stream-tools')
  await page.getByRole('button', { name: '运行记录', exact: true }).click()
  await page.getByRole('button', { name: '查看过程', exact: true }).first().waitFor()
  assert((await page.locator('.aw-table').innerText()).includes('计算设备风险'))
  checks.push({ flow: 'G/K', operation: 'real UI streaming risk question and persisted run visible', result: 'passed' })
  await screenshot('agent-run-history')
  await page.reload()
  await page.getByRole('button', { name: '运行记录', exact: true }).click()
  await page.getByRole('button', { name: '查看过程', exact: true }).first().waitFor()
  assert((await page.locator('.aw-table').innerText()).includes('计算设备风险'))
  await page.getByRole('button', { name: '配置与调试', exact: true }).click()
  await chat.getByRole('button', { name: '新会话', exact: true }).click()
  await chat.getByRole('textbox', { name: '调试问题', exact: true }).fill('请确认工单处置')
  await chat.getByRole('button', { name: '发送', exact: true }).click()
  await chat.getByRole('button', { name: '拒绝执行', exact: true }).waitFor()
  await Promise.all([page.waitForResponse(r => /\/actions\/[^/]+\/confirm$/.test(new URL(r.url()).pathname) && r.status() === 200),
    chat.getByRole('button', { name: '拒绝执行', exact: true }).click()])
  await chat.getByText('已拒绝', { exact: false }).first().waitFor()
  checks.push({ flow: 'F/G', operation: 'UI refusal changes persisted approval without dispatch', result: 'passed' })
  await page.setViewportSize({ width: 390, height: 844 })
  const composer = chat.getByRole('textbox', { name: '调试问题', exact: true })
  await composer.scrollIntoViewIfNeeded()
  const box = await composer.boundingBox()
  assert(box && box.x >= 0 && box.x + box.width <= 391 && box.y >= 0 && box.y < 844,
    'Narrow viewport must allow scrolling to and using the composer')
  await composer.fill('窄窗口控件可输入')
  assert(await chat.getByRole('button', { name: '发送', exact: true }).isEnabled())
  await composer.fill('')
  await screenshot('narrow-agent-rejected')
  assert(errors.length === 0, errors.join('\n'))
  assert(network.every(r => r.status < 400), JSON.stringify(network.filter(r => r.status >= 400)))
  await writeFile(path.join(evidence, 'result.json'), JSON.stringify({ status: 'passed', checks, network, errors,
    scope: 'Real UI operations on API-created Skill/Agents and browser-created ontology; controlled local OpenAI protocol, production lifespan.' }, null, 2))
  console.log(JSON.stringify({ status: 'passed', checks: checks.length, evidence }))
} catch (error) {
  await writeFile(path.join(evidence, 'failure.json'), JSON.stringify({ error: error.message, url: page.url(), checks, network, errors }, null, 2))
  throw error
} finally { await browser.close() }
