// Run against an isolated fixture only; does not write business data.
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')

const base = process.env.UI_AUDIT_URL || 'http://127.0.0.1:5178'
const api = process.env.UI_AUDIT_API || 'http://127.0.0.1:5065/api/v1'
const stage = process.env.UI_AUDIT_STAGE || 'after'
const evidence = path.resolve(__dirname, '../../docs/ui-audit/evidence', stage)
fs.mkdirSync(evidence, { recursive: true })

async function main() {
  const manifest = JSON.parse(
    fs.readFileSync('/private/tmp/ontology-agent-skills-browser-fixture.json'),
  )
  if (!manifest.api_url.startsWith('http://127.0.0.1:'))
    throw new Error('An isolated local fixture is required')
  const login = await fetch(api + '/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: manifest.password }),
  }).then((r) => r.json())
  if (!login.token) throw new Error('Fixture login failed')
  const browser = await chromium.launch({ headless: true, channel: 'chrome' })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  await context.addInitScript(
    ({ token, refresh }) => {
      try {
        localStorage.setItem('token', token)
        localStorage.setItem('refresh_token', refresh)
        localStorage.setItem('theme', 'light')
      } catch {
        /* Chrome's failed editor iframe has an opaque origin. */
      }
    },
    { token: login.token, refresh: login.refresh_token },
  )
  const page = await context.newPage()
  const report = {
    stage,
    browser: await browser.version(),
    pages: [],
    console: [],
    network: [],
    editorConsole: [],
  }
  page.on('pageerror', (e) =>
    report.console.push({ url: page.url(), type: 'pageerror', message: e.message }),
  )
  page.on('console', (m) => {
    if (m.type() !== 'error') return
    const item = { url: page.url(), source: m.location().url, type: 'console', message: m.text() }
    if (m.location().url.startsWith('http://127.0.0.1:8443')) report.editorConsole.push(item)
    else report.console.push(item)
  })
  page.on('response', (r) => {
    if (r.status() >= 400 && r.url().includes('/api/'))
      report.network.push({ url: r.url(), status: r.status() })
  })
  const routes = [
    ['login', '/login'],
    ['dashboard', '/dashboard'],
    ['connections', '/data/connections'],
    ['assets', '/data/assets'],
    ['ontologies', '/ontology/list'],
    ['ontology-ops', '/ontology/list/ops'],
    ['builder', '/builder'],
    ['template', '/builder/template'],
    ['document', '/builder/doc'],
    ['ai-builder', '/builder/ai'],
    ['functions', '/logic/functions'],
    ['function-code', '/logic/functions/risk/code'],
    ['actions', '/logic/actions'],
    ['action-code', '/logic/actions/ticket/code'],
    ['publish', '/ontology/publish'],
    ['mcp', '/service/mcp'],
    ['agents', '/agent/manage'],
    ['agent-new', '/agent/manage/new'],
    ['agent', '/agent/manage/fixture-agent'],
    ['skills', '/skills'],
    ['skill-new', '/skills/new'],
    ['skill', '/skills/' + manifest.skill_id],
    ['settings', '/ops/config'],
  ]
  const names = process.env.UI_AUDIT_PAGES?.split(',')
  const selectedRoutes = names ? routes.filter(([name]) => names.includes(name)) : routes
  try {
    for (const size of [
      { width: 1440, height: 900 },
      { width: 1280, height: 720 },
    ]) {
      await page.setViewportSize(size)
      for (const [name, route] of selectedRoutes) {
        console.log(stage, size.width, name)
        try {
          await page.goto(base + route, { waitUntil: 'networkidle', timeout: 30000 })
          await page.waitForTimeout(300)
          if (name.endsWith('-code') && stage === 'after') {
            const editor = page.frameLocator('.code-server-page__iframe')
            await editor.getByText('main.py', { exact: true }).first().waitFor({ timeout: 15000 })
            await page.waitForTimeout(1000)
            const restricted = editor.getByRole('button', { name: "No, I don't trust the authors" })
            if (await restricted.isVisible()) await restricted.click()
            await page.waitForTimeout(300)
            await editor.getByText('main.py', { exact: true }).first().dblclick()
            await editor.locator('.monaco-editor textarea').first().waitFor()
          }
          const metrics = await page.evaluate(() => {
            const main = document.querySelector('.app-content')
            return {
              title: document.title,
              text: document.body.innerText.slice(0, 500),
              mainText: main?.textContent?.trim().slice(0, 150),
              contentPresent: !main || main.children.length > 0,
              width: document.documentElement.clientWidth,
              scrollWidth: document.documentElement.scrollWidth,
              mainWidth: main?.clientWidth,
              mainScrollWidth: main?.scrollWidth,
            }
          })
          await page.screenshot({ path: path.join(evidence, `${size.width}-${name}.png`) })
          report.pages.push({
            name,
            route,
            viewport: size,
            ...metrics,
            screenshot: `${stage}/${size.width}-${name}.png`,
          })
          if (!metrics.contentPresent) throw new Error('The application content did not render')
        } catch (error) {
          report.pages.push({ name, route, viewport: size, error: error.message })
        }
      }
    }
  } finally {
    if (names && fs.existsSync(path.join(evidence, 'coverage.json'))) {
      const previous = JSON.parse(fs.readFileSync(path.join(evidence, 'coverage.json')))
      report.pages = [...previous.pages.filter((p) => !names.includes(p.name)), ...report.pages]
      const affectedRoutes = selectedRoutes.map(([, route]) => base + route)
      report.console = [
        ...previous.console.filter((p) => !affectedRoutes.includes(p.url)),
        ...report.console,
      ]
      report.network = [
        ...previous.network.filter((p) => !affectedRoutes.some((route) => p.url.startsWith(route))),
        ...report.network,
      ]
    }
    fs.writeFileSync(path.join(evidence, 'coverage.json'), JSON.stringify(report, null, 2))
    await browser.close()
  }
}
main().catch((e) => {
  console.error(e)
  process.exitCode = 1
})
