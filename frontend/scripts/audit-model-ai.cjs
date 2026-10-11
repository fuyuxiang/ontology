// Run only against the isolated backend/tests/run_agent_skills_browser_fixture.py data.
const api = process.env.UI_AUDIT_API || 'http://127.0.0.1:5065/api/v1'
const base = process.env.UI_AUDIT_URL || 'http://127.0.0.1:5178'
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const fs = require('fs')
const path = require('path')
const assert = require('assert')
fs.mkdirSync(path.resolve(__dirname, '../../docs/ui-audit/evidence/after'), { recursive: true })
;(async () => {
  const login = await fetch(api + '/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'Fixture123!' }),
  }).then((r) => r.json())
  const browser = await chromium.launch({ headless: true, channel: 'chrome' })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  await context.addInitScript((token) => {
    localStorage.setItem('token', token)
    localStorage.setItem('theme', 'light')
  }, login.token)
  const p = await context.newPage()
  const report = { checks: [], errors: [] }
  p.on('pageerror', (e) => report.errors.push(e.message))
  try {
    await p.goto(base + '/ontology/list')
    const session = {
      sessionId: 'ui-model-ai-review',
      ontologyName: 'AI建议归属回归',
      buildMethod: 'manual',
      status: 'pending_review',
      createdBy: 'UI评审',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ontologyObjects: ['Device', 'Order'].map((name, index) => ({
        id: 'ui-draft-' + index,
        name,
        displayName: index ? '工单' : '设备',
        tier: 1,
        primaryKey: 'id',
        description: '协议测试对象',
        icon: '🔷',
        instanceCount: 0,
        properties: [
          { id: 'p-' + index, name: 'id', type: 'integer', displayName: '编号', required: true },
        ],
        derivedProperties: [],
        actions: [],
        approved: true,
      })),
      ontologyRelations: [],
      hints: { suggested_actions: [] },
      selectedAssetIds: [],
      selectedSampleSourceIds: [],
      approvedScenarios: [],
      thresholdChanges: [],
      reviewLog: [],
      businessRules: [],
    }
    await p.evaluate((s) => {
      localStorage.setItem('builder-sessions', JSON.stringify([s]))
      localStorage.setItem('builder-active-session', s.sessionId)
    }, session)
    await p.route('**/builder/suggest-attributes', async (route) => {
      await new Promise((r) => setTimeout(r, 350))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          suggested_properties: [
            { name: 'suggested_flag', displayName: '建议标志', type: 'string' },
          ],
        }),
      })
    })
    let relationPayload
    await p.route('**/builder/suggest-relations', (route) => {
      relationPayload = route.request().postDataJSON()
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          suggested_relations: [
            {
              source: 'Device',
              target: 'Order',
              name: 'has_order',
              displayName: '创建工单',
              cardinality: '1:N',
            },
          ],
        }),
      })
    })
    await p.goto(base + '/builder')
    await p.locator('.step2-root').waitFor()
    await p.getByRole('button', { name: 'AI 补全', exact: true }).click()
    await p.locator('.step2-story-item').filter({ hasText: '工单' }).click()
    await p.getByText('AI 补全了 1 个属性', { exact: true }).waitFor()
    let saved = await p.evaluate(() => JSON.parse(localStorage.getItem('builder-sessions'))[0])
    assert(saved.ontologyObjects[0].properties.some((x) => x.name === 'suggested_flag'))
    assert(!saved.ontologyObjects[1].properties.some((x) => x.name === 'suggested_flag'))
    report.checks.push(
      '建议属性响应延迟350ms时切换设备→工单，新增属性仅写原请求设备，未污染当前工单',
    )
    await p.getByRole('button', { name: 'AI 推断', exact: true }).click()
    await p.getByText('AI 推断了 1 条关系', { exact: true }).waitFor()
    saved = await p.evaluate(() => JSON.parse(localStorage.getItem('builder-sessions'))[0])
    assert.equal(saved.ontologyRelations[0].source, 'ui-draft-0')
    assert.equal(saved.ontologyRelations[0].target, 'ui-draft-1')
    assert((await p.locator('.step2-rel-row').innerText()).includes('设备'))
    assert((await p.locator('.step2-rel-row').innerText()).includes('工单'))
    assert.equal(relationPayload.objects[0].name, 'Device')
    await p.getByRole('button', { name: 'AI 推断', exact: true }).click()
    await p.getByText('没有新关系可推断', { exact: true }).waitFor()
    assert.equal(relationPayload.existing_relations[0].source, 'Device')
    assert.equal(relationPayload.existing_relations[0].target, 'Order')
    saved = await p.evaluate(() => JSON.parse(localStorage.getItem('builder-sessions'))[0])
    assert.equal(saved.ontologyRelations.length, 1)
    report.checks.push(
      '建议关系返回对象name后正确映射draft id，图谱/中文关系可读，再次推断不重复；请求已有关系转API约定name',
    )
    await p.waitForTimeout(260)
    await p.screenshot({
      path: path.resolve(__dirname, '../../docs/ui-audit/evidence/after/model-1440-ai-review.png'),
      fullPage: true,
    })
  } catch (e) {
    report.errors.push(e.stack)
  } finally {
    fs.writeFileSync(
      path.resolve(__dirname, '../../docs/ui-audit/evidence/after/audit-model-ai-results.json'),
      JSON.stringify(report, null, 2),
    )
    console.log(report)
    await browser.close()
    if (report.errors.length) process.exitCode = 1
  }
})()
