// Run only against the isolated backend/tests/run_agent_skills_browser_fixture.py data.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const fs = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const api = process.env.UI_AUDIT_API || 'http://127.0.0.1:5065/api/v1'
const base = process.env.UI_AUDIT_URL || 'http://127.0.0.1:5178'
const out = path.resolve(__dirname, '../../docs/ui-audit/evidence/after')
fs.mkdirSync(out, { recursive: true })
const report = { checks: [], screenshots: [], expectedFailures: [], errors: [] }

async function request(endpoint, token, body, method = body ? 'POST' : 'GET') {
  const response = await fetch(api + endpoint, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  return { status: response.status, data: await response.json().catch(() => null) }
}

;(async () => {
  let browser
  let token
  const ids = []
  try {
    const login = await request('/auth/login', null, {
      username: 'admin',
      password: 'Fixture123!',
    })
    assert.equal(login.status, 200)
    token = login.data.token
    const run = Date.now()
    const entities = []
    for (const [suffix, name] of [
      ['Success', 'UI批删成功对象'],
      ['Retry', 'UI批删重试对象'],
    ]) {
      const created = await request('/entities', token, {
        name: `UiBatch${suffix}${run}`,
        name_cn: name,
        ontology_id: 'ops',
        tier: 3,
        status: 'draft',
        description: 'UI批量部分失败回归：隔离测试对象，运行结束自动清理',
        attributes: [],
      })
      if (created.data?.id) ids.push(created.data.id)
      assert.equal(created.status, 201, JSON.stringify(created.data))
      entities.push(created.data)
      assert.equal((await request(`/entities/${created.data.id}`, token)).status, 200)
    }
    report.checks.push('真实隔离后端：ops下创建两条无属性、无关联的草稿对象，实体详情返回200')
    const [success, retry] = entities
    report.entities = { success: success.id, retry: retry.id }
    browser = await chromium.launch({ headless: true, channel: 'chrome' })
    const context = await browser.newContext({ viewport: { width: 1280, height: 720 } })
    await context.addInitScript((value) => {
      localStorage.setItem('token', value)
      localStorage.setItem('theme', 'light')
    }, token)
    const page = await context.newPage()
    page.on('pageerror', (error) => report.errors.push(error.message))
    let confirmations = 0
    page.on('dialog', (dialog) => {
      confirmations++
      dialog.accept()
    })
    const deleteCounts = { success: 0, retry: 0 }
    page.on('request', (req) => {
      if (req.method() !== 'DELETE') return
      const id = new URL(req.url()).pathname.split('/').pop()
      if (id === success.id) deleteCounts.success++
      if (id === retry.id) deleteCounts.retry++
    })
    const failedDelete = `**/entities/${retry.id}`
    let failureStarted
    const started = new Promise((resolve) => {
      failureStarted = resolve
    })
    await page.route(failedDelete, async (route) => {
      if (route.request().method() !== 'DELETE') return route.continue()
      failureStarted()
      await new Promise((resolve) => setTimeout(resolve, 1500))
      return route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'UI批删可控503：仅此测试对象删除失败' }),
      })
    })
    report.expectedFailures.push({ method: 'DELETE', entity: retry.id, status: 503 })
    await page.goto(`${base}/ontology/list/ops`)
    await page.locator('.detail-nav__item').filter({ hasText: '对象定义' }).click()
    const row = (entity) =>
      page.locator('.entities-table tbody tr').filter({ hasText: entity.name })
    await row(success).locator('input[type=checkbox]').check()
    await row(retry).locator('input[type=checkbox]').check()
    await page.getByRole('button', { name: '批量操作', exact: true }).click()
    await page.getByRole('button', { name: '批量删除', exact: true }).click()
    let startTimeout
    try {
      await Promise.race([
        started,
        new Promise((_, reject) => {
          startTimeout = setTimeout(() => reject(new Error('指定DELETE未命中失败注入')), 10000)
        }),
      ])
    } finally {
      clearTimeout(startTimeout)
    }
    await page.getByRole('button', { name: '批量操作', exact: true }).click()
    const pendingButton = page.getByRole('button', { name: '删除中…', exact: true })
    assert(await pendingButton.isDisabled())
    // Also exercise the handler guard: even an injected second event must not issue a new request.
    await pendingButton.dispatchEvent('click')
    assert.equal(confirmations, 1)
    assert.deepEqual(deleteCounts, { success: 1, retry: 1 })
    report.checks.push(
      '删除等待期间显示删除中并禁用；第二点击事件被guard拦截，每条对象仅1次DELETE、仅1次确认',
    )
    await page
      .getByText('1 个对象删除失败，已保留选择；请检查关联数据后重试', { exact: true })
      .waitFor()
    await page.getByText('已删除 1 个对象', { exact: true }).waitFor()
    assert.equal(await row(success).count(), 0)
    assert(await row(retry).locator('input[type=checkbox]').isChecked())
    assert.equal((await request(`/entities/${success.id}`, token)).status, 404)
    assert.equal((await request(`/entities/${retry.id}`, token)).status, 200)
    assert(await page.getByRole('button', { name: '批量删除', exact: true }).isEnabled())
    report.partialResult = {
      success: 404,
      retry: 200,
      retryChecked: true,
      deleteCounts: { ...deleteCounts },
    }
    const screenshot = path.join(out, 'model-1280-batch-partial-failure.png')
    await page.screenshot({ path: screenshot, fullPage: true })
    report.screenshots.push(path.relative(path.resolve(__dirname, '../..'), screenshot))
    report.checks.push(
      '等待结束：成功对象真实404且移出表格，失败对象真实200且仍勾选；反馈准确为成功1/失败1，操作恢复',
    )
    await page.unroute(failedDelete)
    await page.getByRole('button', { name: '批量删除', exact: true }).click()
    await row(retry).waitFor({ state: 'hidden' })
    assert.equal((await request(`/entities/${retry.id}`, token)).status, 404)
    assert.deepEqual(deleteCounts, { success: 1, retry: 2 })
    await page.reload()
    await page.locator('.detail-nav__item').filter({ hasText: '对象定义' }).click()
    await page.locator('.entities-table').waitFor()
    assert.equal(await row(success).count(), 0)
    assert.equal(await row(retry).count(), 0)
    report.checks.push(
      '失败项保留选择直接重试，真实删除返回404；刷新后两条测试对象均不存在，已完成清理',
    )
  } catch (error) {
    report.errors.push(error.stack)
  } finally {
    if (browser) await browser.close()
    for (const id of ids) {
      const cleaned = await request(`/entities/${id}`, token, null, 'DELETE')
      if (![204, 404].includes(cleaned.status))
        report.errors.push(`清理实体${id}失败：${cleaned.status}`)
    }
    fs.writeFileSync(
      path.join(out, 'audit-model-batch-results.json'),
      JSON.stringify(report, null, 2) + '\n',
    )
    console.log(JSON.stringify(report, null, 2))
    if (report.errors.length) process.exitCode = 1
  }
})()
