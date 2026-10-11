const fs = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const stage = process.env.UI_AUDIT_STAGE || 'after'
const base = process.env.UI_AUDIT_URL || 'http://127.0.0.1:5178'
const dir = path.resolve(__dirname, '../../docs/ui-audit/evidence', stage)
const report = { stage, checks: [], errors: [], subpages: [] }

async function main() {
  fs.mkdirSync(dir, { recursive: true })
  const m = JSON.parse(fs.readFileSync('/private/tmp/ontology-agent-skills-browser-fixture.json'))
  const browser = await chromium.launch({ headless: true, channel: 'chrome' })
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } })
  const page = await context.newPage()
  page.setDefaultTimeout(10000)
  page.on('pageerror', (e) => report.errors.push(e.message))
  const shot = (name) => page.screenshot({ path: path.join(dir, `common-${name}.png`) })
  try {
    await page.goto(base + '/ontology/list/ops', { waitUntil: 'networkidle' })
    await page.getByPlaceholder('请输入用户名').fill('admin')
    await page.getByPlaceholder('请输入密码').fill('wrong-password')
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await page.waitForTimeout(1000)
    const errorCount = await page.locator('.login__error').count()
    await shot('login-invalid')
    report.checks.push({ name: 'invalid login inline feedback', errorCount, url: page.url() })
    if (stage === 'before') return
    assert.equal(errorCount, 1)
    assert.ok(page.url().includes('redirect='))
    await page.getByLabel('用户名', { exact: true }).fill('admin')
    await page.getByLabel('密码', { exact: true }).fill(m.password)
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await page.waitForURL('**/ontology/list/ops')
    await page.getByRole('button', { name: '打开用户设置' }).waitFor()
    assert.match(await page.locator('.topbar__user-name').innerText(), /联调admin/)
    await page.reload()
    await page.getByText('联调admin', { exact: true }).waitFor()
    report.checks.push({
      name: 'login returns to requested page; user restored after refresh',
      passed: true,
    })

    const trigger = page.getByRole('button', { name: '打开用户设置' })
    await trigger.focus()
    await page.keyboard.press('Enter')
    await page.getByRole('dialog', { name: '系统设置' }).waitFor()
    assert.ok(
      await page.locator('.settings-dialog').evaluate((el) => el.contains(document.activeElement)),
    )
    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('Tab')
      assert.ok(
        await page
          .locator('.settings-dialog')
          .evaluate((el) => el.contains(document.activeElement)),
      )
    }
    await shot('settings-dialog')
    await page.keyboard.press('Escape')
    await page.getByRole('dialog').waitFor({ state: 'hidden' })
    assert.equal(await trigger.evaluate((el) => el === document.activeElement), true)
    report.checks.push({ name: 'settings Enter, focus loop, Escape, restore focus', passed: true })

    await page.goto(base + '/logic/actions')
    const create = page.getByRole('button', { name: '新建行动' })
    await create.click()
    await page.getByRole('dialog', { name: '创建动作' }).waitFor()
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press('Tab')
      assert.ok(
        await page.locator('.modal-panel').evaluate((el) => el.contains(document.activeElement)),
      )
    }
    await shot('action-dialog')
    await page.keyboard.press('Escape')
    await page.getByRole('dialog').waitFor({ state: 'hidden' })
    assert.equal(await create.evaluate((el) => el === document.activeElement), true)
    report.checks.push({ name: 'shared modal focus loop, Escape, restore focus', passed: true })

    await page.goto(base + '/ontology/list/ops', { waitUntil: 'networkidle' })
    await page.locator('.detail-nav__item').first().waitFor()
    await page.locator('.ontology-detail__content > .attr-panel__loading').waitFor({ state: 'hidden' })
    const navCount = await page.locator('.detail-nav__item').count()
    for (let i = 0; i < navCount; i++) {
      console.log('ontology tab', i)
      const nav = page.locator('.detail-nav__item').nth(i)
      const name = (await nav.innerText()).trim()
      await nav.focus()
      await page.keyboard.press('Enter')
      await page.waitForTimeout(220)
      const text = await page.locator('.ontology-detail').innerText()
      report.subpages.push({
        name,
        state: text.includes('开发中') ? 'existing placeholder' : 'default checked',
      })
      await shot(`ontology-tab-${i}`)
      console.log('ontology tab saved', i)
    }
    await page.goto(base + '/builder')
    for (const value of ['protege', 'webowl', 'vocbench']) {
      await page.locator('.builder-page__select').selectOption(value)
      await page.waitForTimeout(300)
      await shot('builder-' + value)
      report.subpages.push({ name: 'Builder ' + value, state: 'default checked' })
    }

    for (const route of ['/data/assets', '/agent/manage/fixture-agent', '/ontology/publish']) {
      await page.goto(base + route)
      await page.getByRole('button', { name: '打开用户设置' }).click()
      const toggle = page.getByRole('switch', { name: '深色模式' })
      if ((await toggle.getAttribute('aria-checked')) !== 'true') await toggle.click()
      await page.keyboard.press('Escape')
      await page.getByRole('dialog').waitFor({ state: 'hidden' })
      await page.waitForTimeout(300)
      await shot('dark-' + route.split('/').pop())
      report.subpages.push({ name: route, state: 'dark sampled' })
    }
    await page.evaluate(() => {
      localStorage.setItem('theme', 'light')
      document.documentElement.style.zoom = '1.25'
    })
    for (const route of [
      '/ontology/list/ops',
      '/agent/manage/fixture-agent',
      '/ontology/publish',
    ]) {
      await page.goto(base + route)
      await page.evaluate(() => {
        document.documentElement.style.zoom = '1.25'
      })
      await page.waitForTimeout(250)
      const dims = await page.evaluate(() => ({
        client: document.documentElement.clientWidth,
        scroll: document.documentElement.scrollWidth,
        mainClient: document.querySelector('.app-content').clientWidth,
        mainScroll: document.querySelector('.app-content').scrollWidth,
      }))
      await shot('zoom-' + route.split('/').pop())
      report.subpages.push({ name: route, state: 'CSS zoom 125%; viewport 1280×720', ...dims })
    }
  } catch (e) {
    report.errors.push(e.stack)
    await shot('failure')
    throw e
  } finally {
    fs.writeFileSync(path.join(dir, 'common.json'), JSON.stringify(report, null, 2))
    console.log(JSON.stringify(report, null, 2))
    await browser.close()
  }
}
main().catch(() => {
  process.exitCode = 1
})
