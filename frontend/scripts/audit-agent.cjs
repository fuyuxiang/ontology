// Run only against backend/tests/run_agent_skills_browser_fixture.py (isolated local data).
const fs = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const base = process.env.UI_AUDIT_URL || 'http://127.0.0.1:5178'
const manifest = JSON.parse(
  fs.readFileSync('/private/tmp/ontology-agent-skills-browser-fixture.json'),
)
const api = manifest.api_url
if (
  !api.startsWith('http://127.0.0.1:') ||
  !manifest.state_dir.includes('ontology-agent-skills-browser-')
)
  throw new Error('An isolated local fixture is required')
const evidence = path.resolve(__dirname, '../../docs/ui-audit/evidence/after')
fs.mkdirSync(evidence, { recursive: true })
const report = { viewport: { width: 1280, height: 720 }, cases: [], console: [], network: [] }
let token
async function request(url, method = 'GET', body) {
  const response = await fetch(api + url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  })
  const data = response.status === 204 ? null : await response.json()
  if (!response.ok) throw new Error(`${method} ${url}: ${response.status} ${JSON.stringify(data)}`)
  return data
}
async function login(username) {
  return request('/auth/login', 'POST', { username, password: manifest.password })
}
async function shot(page, name) {
  await page.waitForTimeout(300)
  const file = `agent-${name}.png`
  await page.screenshot({ path: path.join(evidence, file) })
  return file
}
async function check(name, fn) {
  console.log(name)
  try {
    const detail = await fn()
    report.cases.push({ name, status: 'passed', ...detail })
  } catch (error) {
    report.cases.push({ name, status: 'failed', error: error.stack })
    console.error(name, error.message)
  }
}
async function main() {
  const auth = await login('admin')
  token = auth.token
  const browser = await chromium.launch({ headless: true, channel: 'chrome' })
  report.browser = await browser.version()
  const context = await browser.newContext({ viewport: report.viewport })
  await context.addInitScript((auth) => {
    try {
      localStorage.setItem('token', auth.token)
      localStorage.setItem('refresh_token', auth.refresh_token)
      localStorage.setItem('theme', 'light')
    } catch {
      // Code Server error frames may have an opaque origin without localStorage.
    }
  }, auth)
  const page = await context.newPage()
  page.on('pageerror', (e) => report.console.push({ url: page.url(), message: e.message }))
  page.on('response', (r) => {
    if (r.status() >= 400 && r.url().includes('/api/'))
      report.network.push({ url: r.url(), status: r.status() })
  })
  const stamp = Date.now()
  const actionName = '评审测试行动 · ' + '需要完整显示的长业务名称'.repeat(5) + ' ' + stamp
  let actionId
  try {
    await check(
      'Action UI creation preserves display name, callable name, and quoted description',
      async () => {
        await page.goto(base + '/logic/actions', { waitUntil: 'networkidle' })
        await page.getByRole('button', { name: '新建行动', exact: true }).click()
        await page.getByPlaceholder('请输入中文名称').fill(actionName)
        await page.getByPlaceholder('请输入英文名称').fill('audit_action_' + stamp)
        await page
          .getByPlaceholder('请输入描述', { exact: true })
          .fill('说明包含"引号"与换行\n创建后保持业务语义。')
        const pending = page.waitForResponse(
          (r) => r.url().endsWith('/api/v1/actions') && r.request().method() === 'POST',
        )
        await page.getByRole('button', { name: '创建', exact: true }).click()
        const response = await pending
        assert.equal(response.status(), 201)
        const value = await response.json()
        actionId = value.id
        await page.waitForURL('**/logic/actions/*/code')
        await page.locator('.code-server-page__title').filter({ hasText: actionName }).waitFor()
        const persisted = await request('/actions/' + actionId)
        assert.equal(persisted.name, actionName)
        assert.equal(persisted.type_config.callable_name, 'audit_action_' + stamp)
        assert.equal(persisted.action_type, 'custom_script')
        return {
          actionId,
          persistedName: persisted.name,
          screenshot: await shot(page, 'created-workspace'),
        }
      },
    )
    await check(
      'Action parameter validation, business success, one request on double click, and search reset',
      async () => {
        assert.ok(actionId)
        await request('/actions/' + actionId, 'PUT', {
          type_config: {
            callable_name: 'audit_action_' + stamp,
            script: "result = {'total': params['a'] + 1}",
          },
          parameters_json: [{ name: 'a', type: 'number', required: true, description: '输入数字' }],
        })
        await page.goto(base + '/logic/actions', { waitUntil: 'networkidle' })
        await page.getByRole('textbox', { name: '搜索行动' }).fill(String(stamp))
        await page.locator('.list-item').filter({ hasText: actionName }).click()
        await page.getByRole('button', { name: '执行', exact: true }).click()
        const dialog = page.getByRole('dialog')
        await dialog.getByRole('button', { name: '执行', exact: true }).click()
        await page.getByText('请填写必填参数：a', { exact: true }).waitFor()
        await page.getByLabel('输入参数（JSON 对象）').fill('[]')
        await dialog.getByRole('button', { name: '执行', exact: true }).click()
        await page.getByText('请输入 JSON 对象，不能使用数组或空值', { exact: true }).waitFor()
        await page.getByLabel('输入参数（JSON 对象）').fill('{')
        await dialog.getByRole('button', { name: '执行', exact: true }).click()
        await page.getByText('参数不是合法 JSON，请检查格式', { exact: true }).waitFor()
        await page.getByLabel('输入参数（JSON 对象）').fill('{"a": 2}')
        let requests = 0
        await page.route('**/actions/' + actionId + '/execute', async (route) => {
          requests++
          const response = await route.fetch()
          await new Promise((resolve) => setTimeout(resolve, 250))
          await route.fulfill({ response })
        })
        await dialog.getByRole('button', { name: '执行', exact: true }).click({ clickCount: 2 })
        await page.getByText('执行成功', { exact: true }).waitFor()
        assert.equal(requests, 1)
        assert.match(await dialog.innerText(), /"total": 3/)
        const persisted = await request('/actions/' + actionId)
        assert.equal(persisted.impact_count, 1)
        const screenshot = await shot(page, 'action-success')
        await page.unroute('**/actions/' + actionId + '/execute')
        await dialog.locator('.btn-secondary').click()
        await page.getByRole('textbox', { name: '搜索行动' }).fill('')
        const all = await request('/actions')
        assert.equal(await page.locator('.list-item').count(), all.length)
        return {
          requests,
          impactCount: persisted.impact_count,
          totalRowsAfterClear: all.length,
          screenshot,
        }
      },
    )
    await check(
      'Action business failure and network failure remain visible and retryable',
      async () => {
        await request('/actions/' + actionId, 'PUT', {
          type_config: { script: "result = params['missing']" },
        })
        await page.goto(base + '/logic/actions', { waitUntil: 'networkidle' })
        await page.locator('.list-item').filter({ hasText: actionName }).click()
        await page.getByRole('button', { name: '执行', exact: true }).click()
        const dialog = page.getByRole('dialog')
        await page.getByLabel('输入参数（JSON 对象）').fill('{"a": 2}')
        await dialog.getByRole('button', { name: '执行', exact: true }).click()
        await page.getByText('执行失败', { exact: true }).waitFor()
        assert.match(await dialog.innerText(), /missing/)
        assert.equal(
          await dialog.getByRole('button', { name: '执行', exact: true }).isEnabled(),
          true,
        )
        const screenshot = await shot(page, 'action-business-failure')
        await page.route('**/actions/' + actionId + '/execute', (route) =>
          route.fulfill({
            status: 503,
            contentType: 'application/json',
            body: JSON.stringify({ detail: '评审注入：执行服务暂时不可用' }),
          }),
        )
        await dialog.getByRole('button', { name: '执行', exact: true }).click()
        await page.getByText('评审注入：执行服务暂时不可用', { exact: true }).waitFor()
        assert.equal(
          await dialog.getByRole('button', { name: '执行', exact: true }).isEnabled(),
          true,
        )
        await page.unroute('**/actions/' + actionId + '/execute')
        return { screenshot, networkFailure: '503 explanation shown; execute button enabled' }
      },
    )
    await check('Logic list failure, retry, local filtering, and keyboard selection', async () => {
      await page.route('**/api/v1/functions', (route) =>
        route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({ detail: '评审注入：逻辑列表不可用' }),
        }),
      )
      await page.goto(base + '/logic/functions', { waitUntil: 'networkidle' })
      await page.getByText('评审注入：逻辑列表不可用', { exact: true }).waitFor()
      const screenshot = await shot(page, 'logic-list-error')
      await page.unroute('**/api/v1/functions')
      await page.getByRole('button', { name: '重试', exact: true }).click()
      await page.locator('.list-item').first().waitFor()
      const before = await page.locator('.list-item').count()
      await page.getByRole('textbox', { name: '搜索逻辑' }).fill('不存在的检索词')
      await page.getByText('无匹配逻辑，请调整搜索或筛选。', { exact: true }).waitFor()
      await page.getByRole('textbox', { name: '搜索逻辑' }).fill('')
      assert.equal(await page.locator('.list-item').count(), before)
      await page.locator('.list-item').first().focus()
      await page.keyboard.press('Enter')
      assert.equal(await page.locator('.list-item').first().getAttribute('aria-pressed'), 'true')
      return { rowCount: before, screenshot }
    })
    await check('AI code HTTP failure and controlled SSE completion/application', async () => {
      await page.goto(base + '/logic/functions?from=builder', { waitUntil: 'networkidle' })
      await page.getByRole('button', { name: 'AI 生成', exact: true }).click()
      await page.getByRole('textbox', { name: '代码生成需求' }).waitFor({ state: 'visible' })
      await page.waitForFunction(
        () => !document.querySelector('textarea[aria-label="代码生成需求"]')?.disabled,
      )
      await page.route('**/ai-code/generate', (route) =>
        route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: '{"detail":"controlled failure"}',
        }),
      )
      await page.getByRole('textbox', { name: '代码生成需求' }).fill('生成简单参数加一')
      await page
        .locator('.ai-code-panel')
        .getByRole('button', { name: '发送', exact: true })
        .click()
      await page.getByText('请求失败：生成请求失败（HTTP 503），请重试', { exact: true }).waitFor()
      const failureScreenshot = await shot(page, 'ai-code-http-failure')
      await page.unroute('**/ai-code/generate')
      const code = "# 中文业务说明\nresult = params['a'] + 1"
      await page.route('**/ai-code/generate', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: `data: ${JSON.stringify({ event: 'chunk', content: code.slice(0, 7) })}\n\ndata: ${JSON.stringify({ event: 'chunk', content: code.slice(7) })}\n\ndata: ${JSON.stringify({ event: 'done', full_code: code })}\n\n`,
        }),
      )
      await page.getByRole('textbox', { name: '代码生成需求' }).fill('请重试')
      await page
        .locator('.ai-code-panel')
        .getByRole('button', { name: '发送', exact: true })
        .click()
      await page.getByRole('button', { name: '应用到编辑器', exact: true }).waitFor()
      assert.equal(await page.locator('.ai-code-panel pre code').last().innerText(), code)
      const screenshot = await shot(page, 'ai-code-complete')
      await page.getByRole('button', { name: '应用到编辑器', exact: true }).click()
      await page.locator('.ai-code-panel').waitFor({ state: 'hidden' })
      assert.equal(
        await page.evaluate(
          (code) =>
            [...document.querySelectorAll('.drawer-panel textarea')].some(
              (input) => input.value === code,
            ),
          code,
        ),
        true,
      )
      await page.unroute('**/ai-code/generate')
      return {
        codeExact: true,
        screenshot,
        failureScreenshot,
        transport: 'controlled SSE event body; byte boundaries separately covered by unit tests',
      }
    })
    let agent, skill
    await check('Agent draft save persistence after reload', async () => {
      const source = await request('/agents/' + manifest.agent_id)
      agent = await request('/agents', 'POST', {
        name: '评审智能体 ' + stamp,
        description: source.description,
        model_id: source.model_id,
        system_prompt: source.system_prompt,
        entity_ids: source.entity_ids,
        tools_config: source.tools_config,
      })
      await page.goto(base + '/agent/manage/' + agent.id, { waitUntil: 'networkidle' })
      await page.getByRole('button', { name: '基本设置', exact: true }).click()
      await page
        .getByPlaceholder('希望智能体帮助完成什么业务任务？')
        .fill('评审保存后的业务目标 ' + stamp)
      await page.getByRole('button', { name: '保存草稿', exact: true }).click()
      await page.getByText('草稿已保存，请调试验证当前配置。', { exact: true }).waitFor()
      await page.reload({ waitUntil: 'networkidle' })
      await page.getByRole('button', { name: '基本设置', exact: true }).click()
      assert.equal(
        await page.getByPlaceholder('希望智能体帮助完成什么业务任务？').inputValue(),
        '评审保存后的业务目标 ' + stamp,
      )
      return { agentId: agent.id, screenshot: await shot(page, 'agent-saved') }
    })
    await check(
      'Agent local fixture SSE success, run record, failure, and continued operation',
      async () => {
        assert.ok(agent)
        await page.getByRole('textbox', { name: '调试问题' }).fill('分析设备告警')
        await page.locator('.aw-chat').getByRole('button', { name: '发送', exact: true }).click()
        await page
          .locator('.aw-markdown')
          .getByText(/设备风险较高/)
          .waitFor({ timeout: 25000 })
        await page.waitForFunction(() =>
          [...document.querySelectorAll('.aw-chat button')].some(
            (button) => button.textContent.trim() === '发送',
          ),
        )
        const runs = await request('/agents/' + agent.id + '/runs')
        assert.ok(runs.length > 0)
        const successScreenshot = await shot(page, 'agent-sse-success')
        await page.getByRole('button', { name: '新会话', exact: true }).click()
        await page.getByRole('textbox', { name: '调试问题' }).fill('故意失败')
        await page.locator('.aw-chat').getByRole('button', { name: '发送', exact: true }).click()
        await page.locator('.aw-chat .aw-error').waitFor({ timeout: 25000 })
        await page.waitForFunction(() =>
          [...document.querySelectorAll('.aw-chat button')].some(
            (button) => button.textContent.trim() === '发送',
          ),
        )
        const failureScreenshot = await shot(page, 'agent-sse-failure')
        await page.getByRole('textbox', { name: '调试问题' }).fill('再次分析设备告警')
        await page.locator('.aw-chat').getByRole('button', { name: '发送', exact: true }).click()
        await page
          .locator('.aw-markdown')
          .getByText(/设备风险较高/)
          .waitFor({ timeout: 25000 })
        return {
          runs: runs.length,
          successScreenshot,
          screenshot: failureScreenshot,
          recoveredAfterFailure: true,
        }
      },
    )
    await check('Skill save persistence and local runtime test success/failure', async () => {
      const source = await request('/skills/' + manifest.skill_id)
      const {
        name,
        description,
        prompt_template,
        input_schema,
        output_schema,
        tools,
        test_cases,
        asset_refs,
        ontology_id,
        ontology_version_id,
        entity_ids,
        applicable_tasks,
        excluded_tasks,
        owner_team,
        visibility,
        tags,
      } = source
      skill = await request('/skills', 'POST', {
        name: name + ' 评审 ' + stamp,
        description,
        prompt_template,
        input_schema,
        output_schema,
        tools,
        test_cases,
        asset_refs,
        ontology_id,
        ontology_version_id,
        entity_ids,
        applicable_tasks,
        excluded_tasks,
        owner_team,
        visibility,
        tags,
      })
      await page.goto(base + '/skills/' + skill.id, { waitUntil: 'networkidle' })
      await page
        .getByPlaceholder('说明技能解决什么业务问题，以及预期价值')
        .fill('技能保存确认 ' + stamp)
      await page.getByRole('button', { name: '保存草稿', exact: true }).click()
      await page.getByText('技能草稿已保存', { exact: true }).waitFor()
      await page.reload({ waitUntil: 'networkidle' })
      assert.equal(
        await page.getByPlaceholder('说明技能解决什么业务问题，以及预期价值').inputValue(),
        '技能保存确认 ' + stamp,
      )
      await page.getByRole('tab', { name: '测试与版本', exact: true }).click()
      await page.getByRole('button', { name: '运行全部', exact: true }).click()
      await page.getByText('业务运行测试通过', { exact: true }).waitFor({ timeout: 25000 })
      const successScreenshot = await shot(page, 'skill-test-success')
      await request('/skills/' + skill.id, 'PUT', {
        test_cases: [{ ...test_cases[0], input: '故意失败' }],
      })
      await page.reload({ waitUntil: 'networkidle' })
      await page.getByRole('tab', { name: '测试与版本', exact: true }).click()
      await page.getByRole('button', { name: '运行全部', exact: true }).click()
      await page
        .getByText('测试未通过，请查看用例结果', { exact: true })
        .waitFor({ timeout: 25000 })
      return {
        skillId: skill.id,
        successScreenshot,
        screenshot: await shot(page, 'skill-test-failure'),
      }
    })
    await check(
      'Agent and Skill creation through UI navigate to saved detail and survive refresh',
      async () => {
        await page.goto(base + '/agent/manage/new', { waitUntil: 'networkidle' })
        await page.getByPlaceholder('输入智能体名称').fill('界面新建智能体 ' + stamp)
        const createdAgent = page.waitForResponse(
          (response) =>
            response.url().endsWith('/api/v1/agents') && response.request().method() === 'POST',
        )
        await page.getByRole('button', { name: '保存草稿', exact: true }).click()
        const agentValue = await (await createdAgent).json()
        await page.waitForURL('**/agent/manage/' + agentValue.id)
        await page.reload({ waitUntil: 'networkidle' })
        await page.getByRole('heading', { name: '界面新建智能体 ' + stamp, exact: true }).waitFor()
        await page.goto(base + '/skills/new', { waitUntil: 'networkidle' })
        await page.getByPlaceholder('例如：设备故障诊断').fill('界面新建技能 ' + stamp)
        const createdSkill = page.waitForResponse(
          (response) =>
            response.url().endsWith('/api/v1/skills') && response.request().method() === 'POST',
        )
        await page.getByRole('button', { name: '保存草稿', exact: true }).click()
        const skillValue = await (await createdSkill).json()
        await page.waitForURL('**/skills/' + skillValue.id)
        await page.reload({ waitUntil: 'networkidle' })
        assert.equal(
          await page.getByPlaceholder('例如：设备故障诊断').inputValue(),
          '界面新建技能 ' + stamp,
        )
        return { agentId: agentValue.id, skillId: skillValue.id }
      },
    )
    await check('Viewer read-only Agent/Skill expression and controls', async () => {
      const viewerAuth = await login('viewer')
      const viewerContext = await browser.newContext({ viewport: { width: 1440, height: 900 } })
      await viewerContext.addInitScript((auth) => {
        try {
          localStorage.setItem('token', auth.token)
          localStorage.setItem('refresh_token', auth.refresh_token)
        } catch {
          // Code Server error frames may have an opaque origin without localStorage.
        }
      }, viewerAuth)
      const viewer = await viewerContext.newPage()
      await viewer.goto(base + '/agent/manage/' + agent.id, { waitUntil: 'networkidle' })
      await viewer
        .getByText('当前账号可查看与调试，修改配置、发布和行动授权需要编辑者或管理员权限。', {
          exact: true,
        })
        .waitFor()
      assert.equal(
        await viewer.getByRole('button', { name: '保存草稿', exact: true }).isDisabled(),
        true,
      )
      const agentScreenshot = await shot(viewer, 'viewer-agent')
      await viewer.goto(base + '/skills/' + skill.id, { waitUntil: 'networkidle' })
      assert.equal(await viewer.getByRole('button', { name: '保存草稿', exact: true }).count(), 0)
      assert.equal(await viewer.getByPlaceholder('例如：设备故障诊断').isDisabled(), true)
      const screenshot = await shot(viewer, 'viewer-skill')
      await viewerContext.close()
      return { agentScreenshot, screenshot }
    })
  } finally {
    fs.writeFileSync(
      path.join(evidence, 'agent-interactions.json'),
      JSON.stringify(report, null, 2),
    )
    await browser.close()
  }
  if (report.cases.some((value) => value.status !== 'passed')) process.exitCode = 1
}
main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
