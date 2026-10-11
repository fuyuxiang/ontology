const fs = require('node:fs'),
  path = require('node:path'),
  assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const out = path.resolve(__dirname, '../../docs/ui-audit/evidence/after')
const report = { checks: [], appErrors: [], editorErrors: [] }
;(async () => {
  const m = JSON.parse(fs.readFileSync('/private/tmp/ontology-agent-skills-browser-fixture.json'))
  assert.ok(m.api_url.startsWith('http://127.0.0.1:5065/'), 'Use the isolated fixture')
  const l = await fetch(m.api_url + '/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: m.password }),
  }).then((r) => r.json())
  const headers = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + l.token }
  const suffix = Date.now()
  const fn = await fetch(m.api_url + '/functions', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      name: '编辑器保存回归逻辑 ' + suffix,
      callable_name: 'ui_editor_' + suffix,
      description: '仅本地隔离测试数据',
      logic_type: 'python',
      ontology_id: 'ops',
    }),
  }).then((r) => r.json())
  assert.ok(fn.id)
  const b = await chromium.launch({ channel: 'chrome', headless: true })
  const c = await b.newContext({ viewport: { width: 1280, height: 720 } })
  await c.addInitScript((t) => {
    try {
      localStorage.setItem('token', t)
      localStorage.setItem('theme', 'light')
    } catch { /* A worker iframe may have an opaque origin. */ }
  }, l.token)
  const p = await c.newPage()
  p.on('pageerror', (e) => report.appErrors.push(e.message))
  p.on('console', (msg) => {
    if (msg.type() === 'error') report.editorErrors.push(msg.text())
  })
  p.setDefaultTimeout(20000)
  try {
    for (const [type, id] of [
      ['functions', fn.id],
      ['actions', 'ticket'],
    ]) {
      await p.goto('http://127.0.0.1:5178/logic/' + type + '/' + id + '/code')
      const iframe = p.frameLocator('.code-server-page__iframe')
      await iframe.locator('body').waitFor()
      const noTrust = iframe.getByRole('button', { name: "No, I don't trust the authors" })
      try {
        await noTrust.waitFor({ timeout: 8000 })
        await noTrust.click()
      } catch { /* Previously opened folders may already be in restricted mode. */ }
      await iframe.getByText('main.py', { exact: true }).first().dblclick()
      const input = iframe.locator('.monaco-editor textarea').first()
      await input.waitFor()
      const folder = await p.locator('.code-server-page__iframe').getAttribute('src')
      const file = path.join(new URL(folder).searchParams.get('folder'), 'main.py')
      const marker = '# ui-audit-editor-save ' + suffix + ' ' + type
      const original = fs.readFileSync(file, 'utf8')
      await input.focus()
      await p.keyboard.press('Meta+End')
      await p.keyboard.insertText('\n' + marker + '\n')
      await p.keyboard.press('Meta+s')
      let saved = false
      for (let i = 0; i < 20; i++) {
        await p.waitForTimeout(150)
        if (fs.readFileSync(file, 'utf8').includes(marker)) {
          saved = true
          break
        }
      }
      assert.ok(saved, 'editor saves workspace file')
      await p.screenshot({ path: path.join(out, 'common-editor-' + type + '-saved.png') })
      await p.waitForTimeout(700)
      await p.reload()
      const re = p.frameLocator('.code-server-page__iframe')
      await re.getByText('main.py', { exact: true }).first().dblclick()
      await re.locator('.monaco-editor textarea').first().waitFor()
      await re.locator('.view-lines').getByText(marker, { exact: false }).waitFor()
      assert.ok(fs.readFileSync(file, 'utf8').includes(marker))
      assert.equal(
        fs
          .readFileSync(file, 'utf8')
          .replace('\n' + marker + '\n', '')
          .trim(),
        original.trim(),
      )
      report.checks.push({
        name: type + ' embedded editor open/save/reload',
        passed: true,
        route: p.url(),
        file: path.basename(path.dirname(file)) + '/main.py',
        displayName: await p.locator('.code-server-page__title').innerText(),
      })
      await p.screenshot({ path: path.join(out, 'common-editor-' + type + '-refresh.png') })
      // Keep fixture code and any pre-existing workspace text after the save check.
      fs.writeFileSync(file, original)
    }
  } finally {
    fs.writeFileSync(path.join(out, 'editor-regression.json'), JSON.stringify(report, null, 2))
    await b.close()
  }
})().catch((e) => {
  console.error(e)
  process.exitCode = 1
})
