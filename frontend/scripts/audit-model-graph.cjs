// Run only against the isolated backend/tests/run_agent_skills_browser_fixture.py data.
const api = process.env.UI_AUDIT_API || 'http://127.0.0.1:5065/api/v1'
const base = process.env.UI_AUDIT_URL || 'http://127.0.0.1:5178'
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('assert')
const path = require('path')
const fs = require('fs')
fs.mkdirSync(path.resolve(__dirname, '../../docs/ui-audit/evidence/after'), { recursive: true })
;(async () => {
  const token = (
    await fetch(api + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'Fixture123!' }),
    }).then((r) => r.json())
  ).token
  const b = await chromium.launch({ headless: true, channel: 'chrome' })
  const c = await b.newContext({ viewport: { width: 1280, height: 720 } })
  await c.addInitScript((t) => {
    localStorage.setItem('token', t)
    localStorage.setItem('theme', 'light')
  }, token)
  const p = await c.newPage()
  const report = { checks: [], errors: [] }
  p.on('pageerror', (e) => report.errors.push(e.message))
  try {
    await p.route('**/entities?ontology_id=ops', (r) =>
      r.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'ui-graph-device',
            name: 'UiGraphDevice',
            name_cn: '超长设备对象名称用于验证图谱节点完整说明和可读性',
            tier: 1,
            attr_count: 3,
            status: 'active',
          },
          {
            id: 'ui-graph-order',
            name: 'UiGraphOrder',
            name_cn: '维修工单对象用于验证两节点关联',
            tier: 2,
            attr_count: 3,
            status: 'active',
          },
        ]),
      }),
    )
    await p.route('**/relations?ontology_id=ops', (r) =>
      r.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'ui-graph-relation',
            name: 'creates_order',
            description: '设备创建维修工单的长关系说明用于验证完整提示',
            from_entity_id: 'ui-graph-device',
            to_entity_id: 'ui-graph-order',
            from_entity_name: 'UiGraphDevice',
            to_entity_name: 'UiGraphOrder',
            cardinality: '1:N',
            rel_type: 'association',
          },
        ]),
      }),
    )
    await p.goto(base + '/ontology/list/ops')
    for (const name of ['导入Excel', '测试', '仿真', '保存']) {
      const button = p.getByRole('button', { name, exact: true })
      assert(await button.isDisabled())
      assert((await button.getAttribute('title')).includes('开发中'))
    }
    assert(await p.getByRole('button', { name: '发布', exact: true }).isEnabled())
    await p.locator('.detail-nav__item').filter({ hasText: '对象定义' }).click()
    await p.locator('.entities-table tbody input[type=checkbox]').first().check()
    await p.getByRole('button', { name: '批量操作', exact: true }).click()
    for (const name of ['批量激活', '批量导出']) {
      const button = p.getByRole('button', { name, exact: true })
      assert(await button.isDisabled())
      assert((await button.getAttribute('title')).includes('开发中'))
    }
    assert(await p.getByRole('button', { name: '批量删除', exact: true }).isEnabled())
    report.checks.push(
      '详情6个未实现操作明确禁用并提供开发中说明，已有发布与选择后的批量删除保持可用',
    )
    await p.locator('.detail-nav__item').filter({ hasText: '本体图谱' }).click()
    await p.locator('.graph-node').nth(1).waitFor()
    await p.waitForTimeout(200)
    let box = await p.locator('.graph-controls').boundingBox()
    assert(box.y + box.height <= 720)
    assert(box.x + box.width <= 1280)
    assert.equal(await p.locator('.graph-node').count(), 2)
    assert((await p.locator('.graph-node title').first().textContent()).includes('超长设备'))
    const initial = await p.locator('.graph-canvas-svg').getAttribute('viewBox')
    await p.getByRole('button', { name: '放大画布', exact: true }).click()
    assert.notEqual(await p.locator('.graph-canvas-svg').getAttribute('viewBox'), initial)
    await p.getByRole('button', { name: '重置画布视图', exact: true }).click()
    await p.waitForTimeout(200)
    await p.screenshot({
      path: path.resolve(
        __dirname,
        '../../docs/ui-audit/evidence/after/model-1280-graph-long-names.png',
      ),
      fullPage: true,
    })
    report.checks.push(
      '1280×720图谱两节点与长名称/长关系协议夹具：底部工具栏完全在视口内，放大改变viewBox，重置可操作，完整名称SVG title保留，截图已保存',
    )
    await p.setViewportSize({ width: 1440, height: 900 })
    box = await p.locator('.graph-controls').boundingBox()
    assert(box.y + box.height <= 900)
    await p.screenshot({
      path: path.resolve(
        __dirname,
        '../../docs/ui-audit/evidence/after/model-1440-graph-long-names.png',
      ),
      fullPage: true,
    })
    report.checks.push('1440×900同图谱工具栏完全可见')
  } catch (e) {
    report.errors.push(e.stack)
  } finally {
    await b.close()
    fs.writeFileSync(
      path.resolve(__dirname, '../../docs/ui-audit/evidence/after/audit-model-graph-results.json'),
      JSON.stringify(report, null, 2),
    )
    console.log(report)
    if (report.errors.length) process.exitCode = 1
  }
})()
