// Run only against the isolated backend/tests/run_agent_skills_browser_fixture.py data.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const fs = require('fs')
const path = require('path')
const assert = require('assert')
const api = process.env.UI_AUDIT_API || 'http://127.0.0.1:5065/api/v1'
const base = process.env.UI_AUDIT_URL || 'http://127.0.0.1:5178'
const out = path.resolve(__dirname, '../../docs/ui-audit/evidence/after')
fs.mkdirSync(out, { recursive: true })
const report = { checks: [], screenshots: [], expectedFailures: [], errors: [] }
async function req(url, token, body, method = body ? 'POST' : 'GET') {
  const r = await fetch(api + url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  const d = await r.json().catch(() => null)
  return { status: r.status, data: d }
}
function check(x) {
  report.checks.push(x)
  console.log(x)
}
;(async () => {
  const login = await req('/auth/login', null, { username: 'admin', password: 'Fixture123!' })
  assert.equal(login.status, 200)
  const token = login.data.token
  const browser = await chromium.launch({ headless: true, channel: 'chrome' })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  await context.addInitScript((t) => {
    localStorage.setItem('token', t)
    localStorage.setItem('theme', 'light')
  }, token)
  const page = await context.newPage()
  page.on('pageerror', (e) => report.errors.push(e.message))
  page.on('dialog', (d) => d.accept())
  async function screenshot(name) {
    await page.waitForTimeout(260)
    const file = out + '/model-' + name + '.png'
    await page.screenshot({ path: file, fullPage: true })
    report.screenshots.push(path.relative(path.resolve(__dirname, '../..'), file))
  }
  let draft
  try {
    await page.goto(base + '/ontology/publish')
    await page.locator('.onto-card').filter({ hasText: '设备运维' }).click()
    await page.locator('.meta-card').waitFor()
    await page.getByRole('button', { name: '创建新版本', exact: true }).click()
    assert.equal(await page.getByRole('dialog').count(), 1)
    await page.getByPlaceholder('请输入版本名称').fill('UI浏览器评审草稿')
    const created = page.waitForResponse(
      (r) => r.url().endsWith('/ontology-publish/versions') && r.request().method() === 'POST',
    )
    await page.getByRole('dialog').getByRole('button', { name: '创建', exact: true }).click()
    const result = await created
    assert.equal(result.status(), 200)
    draft = (await result.json()).id
    await page.locator('.meta-card').filter({ hasText: 'UI浏览器评审草稿' }).waitFor()
    assert((await page.locator('.version-sidebar').innerText()).includes('UI浏览器评审草稿'))
    await screenshot('1440-version-created')
    await page.reload()
    await page.locator('.onto-card').filter({ hasText: '设备运维' }).click()
    await page.locator('.version-item').filter({ hasText: 'UI浏览器评审草稿' }).click()
    await page.locator('.meta-card').filter({ hasText: 'UI浏览器评审草稿' }).waitFor()
    check('真实后端：创建版本带 ontology_id=ops，侧栏更新，刷新后草稿可选且仍归属设备运维')
    await page.getByRole('button', { name: '+ 添加实体', exact: true }).click()
    await page.getByRole('dialog').waitFor()
    const selector = await page.getByRole('dialog').innerText()
    assert(selector.includes('设备'))
    assert(!selector.includes('客户'))
    await screenshot('1440-version-candidates')
    await page.keyboard.press('Escape')
    await page.getByRole('dialog').waitFor({ state: 'hidden' })
    check('真实后端：添加实体仅列设备运维对象，客户本体对象未混入；弹窗Escape关闭')
    await page.route('**/ontology-publish/versions/*/check', (route) =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'UI评审可控检查失败' }),
      }),
    )
    await page.getByRole('button', { name: '一致性检查', exact: true }).click()
    await page.getByText('UI评审可控检查失败', { exact: true }).waitFor()
    assert(await page.getByRole('button', { name: '一致性检查', exact: true }).isEnabled())
    await screenshot('1440-version-check-error')
    await page.unroute('**/ontology-publish/versions/*/check')
    await page.getByRole('button', { name: '一致性检查', exact: true }).click()
    await page.locator('.check-card').waitFor()
    check('Check 500可控注入：错误反馈明确，loading释放，同按钮再次真实检查取得结果')
    await page.getByRole('button', { name: '预览影响', exact: true }).click()
    await page.getByRole('dialog').waitFor()
    await screenshot('1440-version-impact')
    await page.keyboard.press('Escape')
    await page.getByRole('dialog').waitFor({ state: 'hidden' })
    await page.setViewportSize({ width: 1280, height: 720 })
    await screenshot('1280-version')
    check('发布详情1440×900/1280×720与影响弹窗已截图，真实查看另记录')
    await page.goto(base + '/ontology/list/ops')
    await page.getByRole('button', { name: /对象定义/ }).click()
    await page.locator('.entities-table').waitFor()
    const entity = (await req('/entities?ontology_id=ops', token)).data[0]
    await page.route('**/entities/' + entity.id, (route) =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'UI属性加载失败' }),
      }),
    )
    await page
      .locator('.entities-table tbody tr')
      .filter({ hasText: '设备' })
      .locator('.entities-table__action-btn')
      .first()
      .click()
    await page.getByText('对象属性加载失败，请重新加载', { exact: true }).waitFor()
    assert(!(await page.getByText('该对象暂无属性', { exact: true }).isVisible()))
    await screenshot('1280-attribute-error')
    await page.unroute('**/entities/' + entity.id)
    await page.getByRole('button', { name: '重新加载', exact: true }).click()
    await page.locator('.attr-card').first().waitFor()
    check('属性详情500：显示失败而非空数据，重试真实请求后恢复属性')
    const tables = [
      {
        asset_id: 'ui-audit-asset-a',
        table_name: 'ui_fixture_devices_a',
        columns: [{ name: 'id', type: 'integer', comment: '设备编号', is_pk: true }],
      },
      {
        asset_id: 'ui-audit-asset-b',
        table_name: 'ui_fixture_devices_b',
        columns: [{ name: 'device_pk', type: 'integer', comment: '设备主键', is_pk: true }],
      },
    ]
    const session = {
      sessionId: 'ui-model-regression-session',
      ontologyName: 'UI评审本体',
      buildMethod: 'manual',
      status: 'pending_hydration',
      createdBy: 'UI评审',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ontologyObjects: [
        {
          id: 'ui-device-object',
          name: 'UiAuditDevice',
          displayName: 'UI评审设备（协议测试）',
          tier: 1,
          description: '仅浏览器协议夹具，不接外部数据库',
          primaryKey: 'id',
          icon: '🔷',
          instanceCount: 0,
          properties: [
            {
              id: 'ui-prop-id',
              name: 'id',
              displayName: '设备编号',
              type: 'integer',
              required: true,
            },
          ],
          derivedProperties: [],
          actions: [],
          approved: true,
        },
      ],
      ontologyRelations: [],
      hints: { suggested_actions: [] },
      selectedAssetIds: [],
      selectedSampleSourceIds: [],
      approvedScenarios: [],
      thresholdChanges: [],
      reviewLog: [],
      businessRules: [],
    }
    await page.evaluate((s) => {
      localStorage.setItem('builder-sessions', JSON.stringify([s]))
      localStorage.setItem('builder-active-session', s.sessionId)
    }, session)
    await page.route('**/assets/tree', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          tree: [
            {
              connection_id: 'ui-fixture-connection',
              connection_name: 'UI协议测试连接',
              db_type: 'sqlite',
              database: 'ui_fixture',
              tables,
            },
          ],
        }),
      }),
    )
    await page.route('**/builder/suggest-columns', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ suggestions: [] }),
      }),
    )
    await page.route('**/assets/ui-audit-asset-*', (route) => {
      const table = tables.find((t) => route.request().url().endsWith(t.asset_id))
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: table.asset_id,
          name: table.table_name,
          alias: table.table_name,
          kind: 'table',
          schema_snapshot: table.columns,
        }),
      })
    })
    await page.goto(base + '/builder?from=ontology-detail&code=ops&ontology_id=ops')
    await page.locator('.mapping-root').waitFor()
    await page.getByRole('button', { name: '关联', exact: true }).nth(0).click()
    await page.locator('.mapping-table .ant-select').click()
    await page.getByTitle('id (integer)', { exact: true }).click()
    let saved = await page.evaluate(() => JSON.parse(localStorage.getItem('builder-sessions'))[0])
    assert.equal(saved.ontologyObjects[0].properties[0].source_column, 'id')
    assert.equal(saved.ontologyObjects[0].properties[0].source_asset_id, 'ui-audit-asset-a')
    assert.deepEqual(saved.ontologyObjects[0].backing_asset_ids, ['ui-audit-asset-a'])
    check('人工关联+选字段：浏览器保存 source_column=id 与独立source_asset_id，backing资产归属持久')
    await page.getByRole('button', { name: '关联', exact: true }).nth(1).click()
    assert(await page.getByRole('button', { name: '开始数据验证 →', exact: true }).isDisabled())
    saved = await page.evaluate(() => JSON.parse(localStorage.getItem('builder-sessions'))[0])
    assert.equal(saved.ontologyObjects[0].properties[0].source_column, undefined)
    assert.equal(saved.ontologyObjects[0].properties[0].source_asset_id, undefined)
    check('改绑数据表清除旧列与旧资产，开始数据验证门禁恢复禁用')
    await page.locator('.mapping-table .ant-select').click()
    await page.getByTitle('device_pk (integer)', { exact: true }).click()
    await page.reload()
    await page
      .locator('.mapping-editor-table')
      .filter({ hasText: 'ui_fixture_devices_b' })
      .waitFor()
    assert((await page.locator('.mapping-table').innerText()).includes('device_pk'))
    await screenshot('1280-mapping')
    check('刷新重新进入映射页：绑定表与原始字段恢复，不丢失持久映射')
    let hydrateCalls = 0
    const bodies = []
    await page.route('**/builder/hydrate', (route) => {
      bodies.push(route.request().postDataJSON())
      hydrateCalls++
      if (hydrateCalls === 1) {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'UI可控验证失败' }),
        })
      }
      return route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body:
          'data: ' +
          JSON.stringify({
            type: 'drill_complete',
            status: 'pass',
            result: {
              phases: [{ key: 'schema', label: '数据源连接与Schema', status: 'pass', metrics: [] }],
              selectedRows: 1,
              selectedColumns: 1,
              selectedSources: 1,
              entityCount: 1,
              relationCount: 0,
            },
          }) +
          '\n\n',
      })
    })
    await page.getByRole('button', { name: '开始数据验证 →', exact: true }).click()
    await page.locator('.step3-root').waitFor()
    await page.getByRole('button', { name: '开始演练', exact: true }).click()
    await page.getByText('演练失败 · 请检查日志后重试', { exact: true }).waitFor()
    assert((await page.locator('.ob-step--active').innerText()).includes('验证发布'))
    assert(await page.getByRole('button', { name: '重新演练', exact: true }).isVisible())
    assert(await page.getByRole('button', { name: '发布至本体工作室', exact: true }).isDisabled())
    report.failureDom = await page.locator('.step3-log__body').innerText()
    console.log('FAILURE LOG', report.failureDom)
    await screenshot('1280-hydrate-failed')
    check('手工4步流程：开始演练后仍在验证发布；可控500显示失败、停止计时、有重试且禁止发布')
    await page.getByRole('button', { name: '重新演练', exact: true }).click()
    await page.getByRole('button', { name: '开始演练', exact: true }).click()
    await page.getByText('演练完成 · 全部通过', { exact: true }).waitFor()
    assert((await page.locator('.ob-step--active').innerText()).includes('验证发布'))
    assert.equal(bodies[1].objects[0].properties[0].source_column, 'device_pk')
    assert.equal(bodies[1].objects[0].properties[0].source_asset_id, 'ui-audit-asset-b')
    await screenshot('1280-hydrate-success')
    check(
      '浏览器SSE协议夹具：失败后重新演练完整成功，hydrate请求发送真实列名和独立资产字段；未连接真实数据库',
    )
    let finalizeBody
    await page.route('**/builder/finalize', (route) => {
      finalizeBody = route.request().postDataJSON()
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          created_entities: 1,
          created_bindings: 1,
          created_relations: 0,
          skipped: 0,
          total: 1,
        }),
      })
    })
    await page.getByRole('button', { name: '发布至本体工作室', exact: true }).click()
    await page.getByRole('button', { name: '确认发布', exact: true }).click()
    await page.locator('.step3-success__title').waitFor()
    assert((await page.locator('.ob-step--active').innerText()).includes('验证发布'))
    assert.equal(finalizeBody.objects[0].properties[0].source_column, 'device_pk')
    assert.equal(finalizeBody.objects[0].properties[0].source_asset_id, 'ui-audit-asset-b')
    await screenshot('1280-builder-published')
    await page.reload()
    await page.locator('.step3-success__title').waitFor()
    check(
      '浏览器finalize协议夹具：成功后会话标为published，仍在第4步，刷新保留成功与原始映射；未宣称真实数据发布',
    )
  } catch (e) {
    report.errors.push(e.stack)
    await screenshot('failure')
    console.error(e)
  } finally {
    if (draft) await req('/ontology-publish/versions/' + draft, token, null, 'DELETE')
    await browser.close()
    fs.writeFileSync(
      path.resolve(__dirname, '../../docs/ui-audit/evidence/after/audit-model-results.json'),
      JSON.stringify(report, null, 2),
    )
    console.log(JSON.stringify(report, null, 2))
    if (report.errors.length) process.exitCode = 1
  }
})()
