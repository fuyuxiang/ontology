// Local isolated fixture only. Creates QA records and removes them after verification.
const fs = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const { execFileSync } = require('node:child_process')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')

const base = process.env.UI_AUDIT_URL || 'http://127.0.0.1:5178'
const api = process.env.UI_AUDIT_API || 'http://127.0.0.1:5065/api/v1'
const manifest = JSON.parse(fs.readFileSync('/private/tmp/ontology-agent-skills-browser-fixture.json'))
const evidence = path.resolve(__dirname, '../../docs/ui-audit/evidence/after')
assert(['127.0.0.1', 'localhost'].includes(new URL(api).hostname))
assert(manifest.state_dir.includes('ontology-agent-skills-browser-'))
assert(api === manifest.api_url, 'The API must be the isolated fixture')
fs.mkdirSync(evidence, { recursive: true })

async function main() {
  const login = await fetch(api + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'admin', password: manifest.password }) }).then(r => r.json())
  assert(login.token, 'Fixture login failed')
  const request = async (route, method = 'GET', body) => {
    const response = await fetch(api + route, { method, headers: { Authorization: 'Bearer ' + login.token, 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) })
    const text = await response.text()
    assert(response.ok, `${method} ${route}: ${response.status} ${text}`)
    return text ? JSON.parse(text) : null
  }
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  await context.addInitScript(({ token, refresh }) => { localStorage.setItem('token', token); localStorage.setItem('refresh_token', refresh); localStorage.setItem('theme', 'light') }, { token: login.token, refresh: login.refresh_token })
  const page = await context.newPage()
  page.setDefaultTimeout(15000)
  const report = { browser: await browser.version(), viewport: '1440×900;1280×720', tests: [], pageErrors: [], consoleErrors: [], networkFailures: [] }
  page.on('pageerror', e => report.pageErrors.push(e.message))
  page.on('console', m => { if (m.type() === 'error') report.consoleErrors.push(m.text()) })
  page.on('response', r => { if (r.status() >= 400 && r.url().includes('/api/')) report.networkFailures.push({ status: r.status(), url: r.url() }) })
  const shot = async name => { await page.screenshot({ path: path.join(evidence, `data-${name}.png`), animations: 'disabled' }) }
  const go = async route => { await page.goto(base + route, { waitUntil: 'networkidle' }); await page.waitForTimeout(200) }
  const field = (scope, label) => scope.locator('.ant-form-item').filter({ has: page.locator('.ant-form-item-label').filter({ hasText: label }) })
  const input = (scope, label) => field(scope, label).locator('input').first()
  const select = async (scope, label, option) => {
    await field(scope, label).locator('.ant-select-selector').click()
    await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option').filter({ hasText: option }).first().click()
  }
  const run = async (name, fn) => {
    if (process.env.UI_AUDIT_TEST_MATCH && !name.includes(process.env.UI_AUDIT_TEST_MATCH)) return
    console.log('data audit:', name)
    try { await fn(); report.tests.push({ name, status: 'passed' }) }
    catch (e) { report.tests.push({ name, status: 'failed', error: e.message }); await shot('failure-' + name.replace(/[^a-z0-9]+/gi, '-')); console.error(name, e.message) }
    finally { await page.unrouteAll({ behavior: 'wait' }) }
  }
  const uid = Date.now().toString(36)
  let connection, uploaded
  let uploadPath
  let alertId
  let oldNotification, oldModels
  const connectionName = `UI QA ${uid} 本地接口连接`
  const assetName = `UI QA ${uid} 长名称资产_用于确认登记刷新持久与卡片展示一致_${'设备手册'.repeat(5)}`
  try {
    await run('connection-create-validation-persistence', async () => {
      await go('/data/connections')
      await page.getByRole('button', { name: /新增数据源/ }).click()
      await page.locator('.cp-cat-card').filter({ hasText: 'HTTP API' }).click()
      const drawer = page.locator('.ant-drawer-content').filter({ hasText: '新增数据源' })
      await drawer.getByRole('button', { name: /^保\s*存$/ }).click()
      await page.getByText('请填写连接名称', { exact: true }).waitFor()
      await shot('connection-validation')
      await input(drawer, '连接名称').fill(connectionName)
      await input(drawer, 'Base URL').fill(manifest.llm_url)
      await drawer.getByRole('button', { name: /^保\s*存$/ }).click()
      await drawer.waitFor({ state: 'hidden' })
      await page.reload({ waitUntil: 'networkidle' })
      connection = (await request('/connections?q=' + encodeURIComponent(connectionName)))[0]
      assert(connection && connection.name === connectionName)
      await page.getByText(connectionName, { exact: true }).first().waitFor()
      await shot('connection-created')
    })
    await run('connection-filter-error-retry', async () => {
      assert(connection, 'A connection is needed')
      await go('/data/connections')
      await page.getByPlaceholder('搜索连接名称 / 主机...').fill('not-found-' + uid)
      await page.getByText('没有匹配的数据源，请调整搜索或筛选条件', { exact: true }).waitFor()
      await page.getByPlaceholder('搜索连接名称 / 主机...').fill(connectionName)
      await page.getByText(connectionName, { exact: true }).first().waitFor()
      await page.route('**/api/v1/connections**', async route => new URL(route.request().url()).pathname === '/api/v1/connections' && route.request().method() === 'GET' ? route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'QA controlled list failure' }) }) : route.continue())
      await page.reload({ waitUntil: 'networkidle' })
      await page.getByText('数据源加载失败', { exact: true }).waitFor()
      await shot('connection-load-failure')
      await page.unrouteAll({ behavior: 'wait' })
      await page.getByRole('button', { name: /^重\s*试$/ }).click()
      await page.getByText(connectionName, { exact: true }).first().waitFor()
      assert.equal(await page.getByText('数据源加载失败', { exact: true }).count(), 0)
    })
    await run('asset-upload-persistence-and-long-text', async () => {
      await go('/data/assets')
      await page.getByRole('button', { name: '新建资产' }).click()
      await page.getByRole('menuitem', { name: '上传文件', exact: true }).click()
      const drawer = page.locator('.ant-drawer-content').filter({ hasText: '上传文件资产' })
      await drawer.locator('input[type=file]').setInputFiles({ name: `qa-${uid}.txt`, mimeType: 'text/plain', buffer: Buffer.from('UI audit isolated document. 长文本用于核对资产上传、保存、刷新与删除。') })
      await input(drawer, '资产名称').fill(assetName)
      await input(drawer, '领域').fill('ui-qa')
      await drawer.locator('textarea').fill('局部视觉评审测试说明。'.repeat(20))
      await drawer.getByRole('button', { name: '上传并注册', exact: true }).click()
      await drawer.waitFor({ state: 'hidden' })
      uploaded = (await request('/assets?q=' + encodeURIComponent(assetName)))[0]
      assert(uploaded && uploaded.name === assetName)
      assert(uploaded.locator.file_path.startsWith(manifest.state_dir), 'The file must stay in the isolated fixture')
      uploadPath = uploaded.locator.file_path
      await page.reload({ waitUntil: 'networkidle' })
      await page.locator('.ap-card__name').filter({ hasText: assetName }).waitFor()
      assert((await page.locator('.ap-card').filter({ hasText: assetName }).locator('.ap-card__desc').evaluate(el => el.clientHeight)) <= 38, 'Descriptions must remain within two readable lines')
      await shot('asset-uploaded-long-text')
      await page.setViewportSize({ width: 1280, height: 720 })
      await shot('asset-uploaded-1280')
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false)
      await page.setViewportSize({ width: 1440, height: 900 })
    })
    await run('asset-list-latest-request-and-error-retry', async () => {
      assert(uploaded, 'An uploaded asset is needed')
      await go('/data/assets')
      await page.route('**/api/v1/assets**', async route => {
        const url = new URL(route.request().url())
        if (url.pathname !== '/api/v1/assets') return route.continue()
        const q = url.searchParams.get('q')
        if (q === 'slow') { await new Promise(resolve => setTimeout(resolve, 900)); return route.fulfill({ json: [{ ...uploaded, id: 'qa-slow', name: 'OLD slow result' }] }) }
        if (q === 'fast') return route.fulfill({ json: [{ ...uploaded, id: 'qa-fast', name: 'NEW fast result' }] })
        return route.continue()
      })
      const search = page.getByPlaceholder('搜索资产名称 / 别名 / 描述...')
      await search.fill('slow')
      await page.waitForTimeout(100)
      await search.fill('fast')
      await page.getByText('NEW fast result', { exact: true }).waitFor()
      await page.waitForTimeout(1100)
      assert.equal(await page.getByText('OLD slow result', { exact: true }).count(), 0)
      await shot('asset-latest-request')
      await page.unrouteAll({ behavior: 'wait' })
      await page.route('**/api/v1/assets**', async route => new URL(route.request().url()).pathname === '/api/v1/assets' ? route.fulfill({ status: 503, json: { detail: 'QA controlled asset failure' } }) : route.continue())
      await page.reload({ waitUntil: 'networkidle' })
      await page.getByText('资产加载失败', { exact: true }).waitFor()
      assert.equal(await page.getByText('暂无资产，点击「新建资产」开始登记', { exact: true }).count(), 0)
      await shot('asset-load-failure')
      await page.unrouteAll({ behavior: 'wait' })
      await page.getByRole('button', { name: /^重\s*试$/ }).click()
      await page.locator('.ap-card__name').filter({ hasText: assetName }).waitFor()
    })
    await run('table-drawer-connection-race-close-reopen', async () => {
      await go('/data/assets')
      const fake = id => ({ ...connection, id, name: id === 'qa-A' ? 'QA Database A' : 'QA Database B', category: 'database', type: 'mysql', enabled: true })
      await page.route('**/api/v1/connections**', async route => {
        const pathname = new URL(route.request().url()).pathname
        if (pathname === '/api/v1/connections') return route.fulfill({ json: [fake('qa-A'), fake('qa-B')] })
        if (pathname.endsWith('/qa-A/tables')) { await new Promise(resolve => setTimeout(resolve, 900)); return route.fulfill({ json: ['old_table_A'] }) }
        if (pathname.endsWith('/qa-B/tables')) return route.fulfill({ json: ['fresh_table_B'] })
        return route.continue()
      })
      await page.getByRole('button', { name: '新建资产' }).click()
      await page.getByRole('menuitem', { name: '表 / SQL 视图', exact: true }).click()
      const drawer = page.locator('.ant-drawer-content').filter({ hasText: '新建结构化资产' })
      await select(drawer, /^连接/, 'QA Database A')
      await select(drawer, /^连接/, 'QA Database B')
      await page.waitForTimeout(1200)
      await field(drawer, '表名').locator('.ant-select-selector').click()
      await page.getByTitle('fresh_table_B', { exact: true }).waitFor()
      assert.equal(await page.getByTitle('old_table_A', { exact: true }).count(), 0)
      await shot('table-connection-race')
      await page.keyboard.press('Escape')
      await drawer.waitFor({ state: 'hidden' })
      await page.getByRole('button', { name: '新建资产' }).click()
      await page.getByRole('menuitem', { name: '表 / SQL 视图', exact: true }).click()
      assert.equal(await input(drawer, '资产名称').inputValue(), '')
      assert.equal(await field(drawer, '表名').locator('.ant-select-selector').innerText(), '')
      await drawer.getByRole('button', { name: 'Close' }).click()
    })
    await run('settings-save-refresh-secret-preservation-model-test', async () => {
      const backup = JSON.parse(execFileSync('python3', ['-c', 'import sqlite3,sys,json; c=sqlite3.connect(sys.argv[1]); print(json.dumps({"notification":[{"key":k,"value":v} for k,v in c.execute("select key,value from system_config where [group]=\'notification\'")],"models":json.loads((c.execute("select value from system_config where key=\'ai.models\'").fetchone() or ["[]"])[0] or "[]")}))', manifest.database], { encoding: 'utf8' }))
      oldNotification = backup.notification
      oldModels = backup.models
      const knownSecret = 'qa-smtp-secret-' + uid
      await request('/system-config', 'PUT', { group: 'notification', items: [{ key: 'smtp_password', value: knownSecret }] })
      await request('/system-config/ai/models', 'PUT', { models: [
        { id: 'qa-model-A', name: 'QA 模型 A 长名称_' + '已配置凭据'.repeat(8), provider: 'OpenAI', model_id: 'fixture-controlled-chat', api_key: 'qa-model-A-real-secret-' + uid, base_url: manifest.llm_url.replace(/\/v1$/, ''), temperature: 0.7, max_tokens: 4096, scenes: ['general'], is_default: false },
        { id: 'qa-model-B', name: 'QA 模型 B', provider: 'OpenAI', model_id: 'fixture-controlled-chat', api_key: 'qa-model-B-real-secret-' + uid, base_url: manifest.llm_url.replace(/\/v1$/, ''), temperature: 0.7, max_tokens: 4096, scenes: ['general'], is_default: true },
      ] })
      await go('/ops/config')
      const notification = page.locator('#config-group-notification')
      const host = notification.locator('.config-field').filter({ has: page.locator('label').filter({ hasText: 'SMTP 服务器地址' }) }).locator('input')
      const initialHost = await host.inputValue()
      await host.fill('smtp-qa.example.test')
      await notification.getByRole('button', { name: '撤销更改', exact: true }).click()
      assert.equal(await host.inputValue(), initialHost)
      await host.fill('smtp-qa.example.test')
      await notification.getByRole('button', { name: /^保\s*存$/ }).click()
      await page.getByText('保存成功', { exact: true }).waitFor()
      const firstModel = page.locator('.model-card').filter({ hasText: 'QA 模型 A' })
      await firstModel.getByRole('button', { name: '设为默认', exact: true }).click()
      await firstModel.getByText('默认', { exact: true }).waitFor()
      execFileSync('python3', ['-c', 'import sqlite3,sys,json; c=sqlite3.connect(sys.argv[1]); assert c.execute("select value from system_config where key=\'smtp_password\'").fetchone()[0]==sys.argv[2]; models=json.loads(c.execute("select value from system_config where key=\'ai.models\'").fetchone()[0]); assert all(m["api_key"]=="qa-model-"+m["id"][-1]+"-real-secret-"+sys.argv[3] for m in models)', manifest.database, knownSecret, uid])
      await page.reload({ waitUntil: 'networkidle' })
      assert.equal(await host.inputValue(), 'smtp-qa.example.test')
      const savedModel = page.locator('.model-card').filter({ hasText: 'QA 模型 A' })
      await savedModel.getByRole('button', { name: /测试连通性/ }).click()
      await savedModel.locator('.model-card__test-result').waitFor()
      assert(!(await savedModel.locator('.model-card__test-result').innerText()).includes('请先填写 API Key'))
      await savedModel.scrollIntoViewIfNeeded()
      await shot('settings-saved-model-test')
      await page.setViewportSize({ width: 1280, height: 720 })
      await page.locator('.config-nav').scrollIntoViewIfNeeded()
      await shot('settings-1280-navigation')
      await page.setViewportSize({ width: 1440, height: 900 })
    })
    await run('mcp-stats-docs-keyboard-and-failure-retry', async () => {
      const stats = await request('/mcp/stats/tools')
      assert(Array.isArray(stats))
      await go('/service/mcp')
      await shot('mcp-overview')
      await page.route('**/api/v1/mcp/stats/tools', route => route.fulfill({ status: 503, json: { detail: 'QA controlled MCP failure' } }))
      await page.reload({ waitUntil: 'networkidle' })
      await page.getByText('部分服务指标加载失败', { exact: true }).waitFor()
      await shot('mcp-stat-failure')
      await page.unrouteAll({ behavior: 'wait' })
      await page.getByRole('button', { name: /^重\s*试$/ }).click()
      await page.getByText('部分服务指标加载失败', { exact: true }).waitFor({ state: 'hidden' })
      await page.getByRole('button', { name: '接入文档', exact: true }).click()
      const tool = page.locator('.tool-card').first()
      await tool.focus()
      await page.keyboard.press('Enter')
      await page.locator('.ant-drawer-content').waitFor()
      await shot('mcp-tool-drawer')
      await page.keyboard.press('Escape')
      await page.locator('.ant-drawer-content').waitFor({ state: 'hidden' })
      await shot('mcp-docs')
    })
    await run('dashboard-default-partial-error-alert-and-range-race', async () => {
      await go('/dashboard')
      await page.getByRole('heading', { name: '系统看板', exact: true }).waitFor()
      await page.getByText('资源使用率', { exact: true }).waitFor()
      await shot('dashboard-default')
      await page.route('**/api/v1/monitor/resources', route => route.fulfill({ status: 503, json: { detail: 'QA controlled resource failure' } }))
      await page.reload({ waitUntil: 'networkidle' })
      await page.getByText('部分看板数据更新失败', { exact: true }).waitFor()
      assert((await page.locator('.last-update').innerText()).includes('--:--:--'))
      assert.equal(await page.locator('.gauge-value').first().innerText(), '—')
      await shot('dashboard-partial-failure')
      await page.unrouteAll({ behavior: 'wait' })
      await page.getByRole('button', { name: '刷新系统看板', exact: true }).click()
      await page.getByText('部分看板数据更新失败', { exact: true }).waitFor({ state: 'hidden' })
      assert(!(await page.locator('.last-update').innerText()).includes('--:--:--'))

      const alertMessage = 'QA persisted alert ' + uid + ' 长告警说明'.repeat(20)
      alertId = Number(execFileSync('python3', ['-c', 'import sqlite3,sys,datetime; c=sqlite3.connect(sys.argv[1]); cur=c.execute("insert into t_alert(level,service_name,message,resolved,created_at) values (?,?,?,?,?)",("warning","QA service",sys.argv[2],0,datetime.datetime.utcnow().isoformat())); c.commit(); print(cur.lastrowid)', manifest.database, alertMessage], { encoding: 'utf8' }).trim())
      await page.getByRole('button', { name: '刷新系统看板', exact: true }).click()
      const row = page.locator('.ant-table-row').filter({ hasText: alertMessage })
      await row.waitFor()
      await page.route('**/api/v1/monitor/alerts/*/resolve', route => route.fulfill({ status: 503, json: { detail: 'QA controlled alert failure' } }))
      await row.getByRole('button', { name: /处\s*理/ }).click()
      await page.getByText('告警处理失败，请重试', { exact: true }).waitFor()
      await row.locator('.ant-btn-loading').waitFor({ state: 'hidden' })
      assert.equal(await row.getByRole('button', { name: /处\s*理/ }).count(), 1)
      await page.unrouteAll({ behavior: 'wait' })
      await row.getByRole('button', { name: /处\s*理/ }).click()
      await page.getByText('告警已处理', { exact: true }).waitFor()
      assert.equal((await request('/monitor/alerts?limit=50')).find(item => item.id === alertId).resolved, true)
      assert.equal(await row.getByRole('button', { name: /处\s*理/ }).count(), 0)
      await row.getByRole('button', { name: /^详\s*情$/ }).click()
      await page.locator('.ant-modal').getByText('已处理', { exact: true }).waitFor()
      await shot('dashboard-alert-resolved-detail')
      await page.keyboard.press('Escape')

      await page.route('**/api/v1/monitor/response-history?**', async route => {
        const hours = new URL(route.request().url()).searchParams.get('hours')
        if (hours === '1') await new Promise(resolve => setTimeout(resolve, 900))
        const metric = hours === '6' ? 80 : 6
        const now = Date.now()
        return route.fulfill({ json: [
          { service_name: '后端API', response_ms: metric - 2, status: 'healthy', collected_at: new Date(now - 60000).toISOString() },
          { service_name: '后端API', response_ms: metric, status: 'healthy', collected_at: new Date(now).toISOString() },
        ] })
      })
      await page.getByText('近1小时', { exact: true }).click()
      await page.getByText('近6小时', { exact: true }).click()
      await page.waitForTimeout(1200)
      await shot('dashboard-response-range-race')
      await page.setViewportSize({ width: 1280, height: 720 })
      await shot('dashboard-1280')
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false)
      await page.setViewportSize({ width: 1440, height: 900 })
    })
    await run('dark-mode-data-defaults-1280', async () => {
      await page.evaluate(() => localStorage.setItem('theme', 'dark'))
      // The init script sets light only for new documents; use a dedicated dark context.
      const darkContext = await browser.newContext({ viewport: { width: 1280, height: 720 } })
      await darkContext.addInitScript(token => { localStorage.setItem('token', token); localStorage.setItem('theme', 'dark') }, login.token)
      const dark = await darkContext.newPage()
      dark.on('pageerror', e => report.pageErrors.push(`dark ${dark.url()}: ${e.message}`))
      for (const [name, route] of [['assets', '/data/assets'], ['connections', '/data/connections'], ['settings', '/ops/config'], ['dashboard', '/dashboard']]) {
        await dark.goto(base + route, { waitUntil: 'networkidle' })
        assert.equal(await dark.locator('html').getAttribute('data-theme'), 'dark')
        await dark.screenshot({ path: path.join(evidence, `data-dark-${name}-1280.png`), animations: 'disabled' })
        assert.equal(await dark.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false)
      }
      await darkContext.close()
    })
    await run('asset-delete-persists-after-refresh', async () => {
      assert(uploaded, 'An uploaded asset is needed')
      await go('/data/assets')
      const card = page.locator('.ap-card').filter({ hasText: assetName })
      await card.getByRole('button', { name: /^删\s*除$/ }).click()
      await page.locator('.ant-popover .ant-btn-primary').click()
      await card.waitFor({ state: 'hidden' })
      await page.reload({ waitUntil: 'networkidle' })
      assert.equal((await request('/assets?q=' + encodeURIComponent(assetName))).length, 0)
      await shot('asset-deleted')
      uploaded = null
    })
    await run('supplementary-component-states', async () => {
      const fakeConnection = { id: 'qa-register', name: 'QA pending registration', category: 'database', type: 'mysql', host: '127.0.0.1', port: 3306, database: 'qa', enabled: true, writable: false }
      let registrations = 0
      await page.route('**/api/v1/connections**', route => {
        const pathname = new URL(route.request().url()).pathname
        if (pathname === '/api/v1/connections') return route.fulfill({ json: [fakeConnection] })
        if (pathname.endsWith('/qa-register/tables')) return route.fulfill({ json: ['qa_pending_table'] })
        return route.continue()
      })
      await page.route('**/api/v1/assets', async route => {
        if (route.request().method() !== 'POST') return route.continue()
        registrations++
        await new Promise(resolve => setTimeout(resolve, 1000))
        return route.fulfill({ json: { ...route.request().postDataJSON(), id: 'qa-register-asset', status: 'active' } })
      })
      await go('/data/connections')
      await page.locator('.ant-table-row').filter({ hasText: fakeConnection.name }).getByRole('button', { name: /列表/ }).click()
      const modal = page.locator('.ant-modal-content').filter({ hasText: '浏览：' })
      await modal.getByRole('tab', { name: '表（1）', exact: true }).click()
      assert.equal(await modal.evaluate(el => Math.round(el.parentElement.getBoundingClientRect().width)), 720)
      const register = modal.getByRole('button', { name: '注册为 Asset', exact: true })
      await register.dblclick()
      await page.keyboard.press('Escape')
      assert(await modal.isVisible(), 'Pending registration must retain its modal')
      assert(await modal.getByRole('button', { name: /批量注册/ }).isDisabled())
      await shot('connection-registration-pending')
      await page.waitForTimeout(1200)
      assert.equal(registrations, 1, 'Repeated input must create only one registration')
      await page.keyboard.press('Escape')
      await modal.waitFor({ state: 'hidden' })
      await page.unrouteAll({ behavior: 'wait' })
      await page.route('**/api/v1/system-config**', route => {
        const pathname = new URL(route.request().url()).pathname
        if (route.request().method() === 'GET' && ['/api/v1/system-config', '/api/v1/system-config/ai/models'].includes(pathname)) return route.fulfill({ status: 503, json: { detail: 'QA controlled configuration failure' } })
        return route.continue()
      })
      await go('/ops/config')
      await page.getByText('系统配置加载失败', { exact: true }).waitFor()
      await page.getByText('模型配置加载失败', { exact: true }).waitFor()
      assert((await page.locator('.config-content').boundingBox()).width > 800, 'Loading wrapper must fill the available content width')
      assert.equal(await page.getByText('暂无模型配置', { exact: true }).count(), 0)
      await page.locator('#config-group-ai').scrollIntoViewIfNeeded()
      await shot('settings-load-failure')
      await page.unrouteAll({ behavior: 'wait' })
      for (const message of ['系统配置加载失败', '模型配置加载失败']) {
        await page.locator('.ant-alert').filter({ hasText: message }).getByRole('button', { name: /^重\s*试$/ }).click()
      }
      await page.locator('#config-group-basic input').first().waitFor()
      assert.equal(await page.getByText('模型配置加载失败', { exact: true }).count(), 0)
      await page.locator('#config-group-notification').scrollIntoViewIfNeeded()
      await page.waitForTimeout(100)
      assert((await page.locator('.config-nav .ant-btn-primary').innerText()).includes('通知配置'))
    })
  } finally {
    if (uploaded) await request('/assets/' + uploaded.id, 'DELETE').catch(e => report.tests.push({ name: 'cleanup-asset', status: 'failed', error: e.message }))
    if (connection) await request('/connections/' + connection.id, 'DELETE').catch(e => report.tests.push({ name: 'cleanup-connection', status: 'failed', error: e.message }))
    if (alertId) execFileSync('python3', ['-c', 'import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute("delete from t_alert where id=? and service_name=?",(int(sys.argv[2]),"QA service")); c.commit()', manifest.database, String(alertId)])
    if (uploadPath && path.resolve(uploadPath).startsWith(path.resolve(manifest.state_dir, 'uploads') + path.sep) && fs.existsSync(uploadPath)) fs.unlinkSync(uploadPath)
    if (oldModels) await request('/system-config/ai/models', 'PUT', { models: oldModels })
    if (oldNotification) await request('/system-config', 'PUT', { group: 'notification', items: oldNotification.map(({ key, value }) => ({ key, value })) })
    const reportName = process.env.UI_AUDIT_REPORT_NAME || 'data-regression.json'
    assert(/^[a-z0-9-]+\.json$/.test(reportName), 'Use a JSON evidence filename without path segments')
    fs.writeFileSync(path.join(evidence, reportName), JSON.stringify(report, null, 2))
    await browser.close()
  }
  console.log(JSON.stringify(report.tests, null, 2))
  if (report.tests.some(t => t.status === 'failed') || report.pageErrors.length) process.exitCode = 1
}
main().catch(e => { console.error(e); process.exitCode = 1 })
