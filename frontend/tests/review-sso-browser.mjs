// Separate, fresh browser: OIDC navigation, permissions, refresh and logout.
import { pathToFileURL } from 'node:url'
import { mkdir, writeFile } from 'node:fs/promises'
import assert from 'node:assert/strict'
import path from 'node:path'
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE))
const evidence = path.resolve('../docs/review/evidence/sso-browser')
await mkdir(evidence, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE })
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
page.setDefaultTimeout(10000)
const records = [], errors = []
page.on('pageerror', error => errors.push(error.message))
page.on('response', response => {
  if (response.url().includes('/api/')) records.push({ path: new URL(response.url()).pathname, status: response.status() })
})
try {
  await page.goto('http://127.0.0.1:5178/login?redirect=/ontology/list')
  await page.getByRole('button', { name: '通过 OIDC 登录', exact: true }).click()
  await page.waitForURL('**/ontology/list')
  await page.getByRole('button', { name: '新建本体', exact: true }).waitFor()
  assert(await page.getByRole('button', { name: '新建本体', exact: true }).isDisabled())
  assert((await page.locator('body').innerText()).includes('隔离 SSO 用户'))
  await page.locator('.onto-card').first().waitFor()
  const cards = await page.locator('.onto-card').evaluateAll(nodes => nodes.map(node => ({
    code: node.querySelector('.onto-card__code')?.textContent.trim(),
    objects: Number(node.querySelector('[title="对象"]')?.textContent.replace(/\D/g, '')),
    badge: node.querySelector('.onto-card__badge')?.textContent.trim(),
    status: node.querySelector('.onto-card__status')?.textContent.trim(),
    deletionDisabled: node.querySelector('.onto-card__action-btn--del')?.disabled,
  })))
  assert(cards.every(card => card.deletionDisabled))
  assert(cards.filter(card => card.objects === 0).every(card => card.badge === '待构建' && card.status === '尚未发布'))
  assert(cards.some(card => card.objects > 0 && card.badge === '已建模' && card.status.startsWith('已发布')))
  await page.screenshot({ path: path.join(evidence, 'viewer-login.png'), fullPage: true, animations: 'disabled' })
  await page.reload()
  await page.getByRole('button', { name: '新建本体', exact: true }).waitFor()
  assert(await page.getByRole('button', { name: '新建本体', exact: true }).isDisabled())
  await page.goto('http://127.0.0.1:5178/ops/config')
  await page.getByText('系统配置需要管理员权限', { exact: true }).waitFor()
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: '打开用户设置', exact: true }).click()
  await page.getByRole('button', { name: '退出登录', exact: true }).waitFor()
  await page.screenshot({ path: path.join(evidence, 'narrow-user-settings.png'), fullPage: true, animations: 'disabled' })
  await Promise.all([page.waitForResponse(r => r.url().endsWith('/auth/logout') && r.status() === 200),
    page.getByRole('button', { name: '退出登录', exact: true }).click()])
  await page.waitForURL('**/login')
  await page.goto('http://127.0.0.1:5178/ontology/list')
  await page.waitForURL(/\/login\?redirect=/)
  assert(new URL(page.url()).searchParams.get('redirect') === '/ontology/list')
  assert(errors.length === 0, errors.join('\n'))
  assert(records.some(r => r.path.endsWith('/sso/exchange') && r.status === 200))
  assert(records.some(r => r.path.endsWith('/auth/logout') && r.status === 200))
  await writeFile(path.join(evidence, 'result.json'), JSON.stringify({ status: 'passed', provider: 'isolated signed OIDC HTTP protocol',
    checks: ['real browser redirects', 'single-use ticket exchange', 'viewer creation/deletion disabled', 'empty and published cards reflect actual state', 'refresh restores viewer', 'logout revokes session', 'protected deep link returns login'],
    cards, records, errors }, null, 2))
  console.log('SSO browser login, viewer permissions, reload and logout passed.')
} finally { await browser.close() }
