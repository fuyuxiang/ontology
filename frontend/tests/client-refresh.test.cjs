const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const ts = require('typescript')

function fixture(refresh) {
  let rejectResponse
  const retries = []
  const client = (config) => {
    retries.push(config)
    return Promise.resolve({ data: 'retried' })
  }
  client.interceptors = {
    request: { use() {} },
    response: {
      use(_success, failure) {
        rejectResponse = failure
      },
    },
  }
  const axios = { create: () => client, post: refresh }
  const storage = new Map([
    ['token', 'expired'],
    ['refresh_token', 'refresh'],
  ])
  const localStorage = {
    getItem: (key) => storage.get(key),
    setItem: (key, value) => storage.set(key, value),
    removeItem: (key) => storage.delete(key),
  }
  const events = []
  const window = { location: { href: '' }, dispatchEvent: event => events.push(event.type) }
  const source = fs
    .readFileSync(require.resolve('../src/api/client.ts'), 'utf8')
    .replace("import.meta.env.VITE_API_BASE_URL || '/api/v1'", "'/api/v1'")
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', 'window', 'localStorage', code)(
    () => axios,
    module,
    module.exports,
    window,
    localStorage,
  )
  const error = () => ({ response: { status: 401 }, config: { headers: {} } })
  function authenticatedFetch(fetch) {
    const source = fs.readFileSync(require.resolve('../src/api/authenticatedFetch.ts'), 'utf8')
    const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
    const loader = { exports: {} }
    new Function('require', 'module', 'exports', 'fetch', output)(() => module.exports, loader, loader.exports, fetch)
    return loader.exports.authenticatedFetch
  }
  return { rejectResponse, retries, storage, window, error, authenticatedFetch, events }
}

test('concurrent expired requests share one refresh and each retry once with the new token', async () => {
  let count = 0
  let resolve
  const f = fixture(() => {
    count++
    return new Promise((r) => {
      resolve = r
    })
  })
  const errors = [f.error(), f.error(), f.error()]
  const pending = errors.map(f.rejectResponse)
  assert.equal(count, 1)
  resolve({ data: { token: 'new-token', refresh_token: 'new-refresh' } })
  await Promise.all(pending)
  assert.equal(f.retries.length, 3)
  assert.ok(f.retries.every((x) => x._retry && x.headers.Authorization === 'Bearer new-token'))
  await assert.rejects(f.rejectResponse(errors[0]))
  assert.equal(count, 1)
})

test('failed refresh rejects every waiting request instead of leaving loading promises pending', async () => {
  let reject
  const f = fixture(
    () =>
      new Promise((_resolve, r) => {
        reject = r
      }),
  )
  const pending = Promise.allSettled([
    f.rejectResponse(f.error()),
    f.rejectResponse(f.error()),
    f.rejectResponse(f.error()),
  ])
  reject(new Error('refresh unavailable'))
  const results = await Promise.race([
    pending,
    new Promise((_resolve, r) => setTimeout(() => r(new Error('requests hung')), 500)),
  ])
  assert.ok(results.every((x) => x.status === 'rejected'))
  assert.equal(f.storage.has('token'), false)
  assert.equal(f.window.location.href, '/login')
  assert.equal(f.retries.length, 0)
})

test('invalid login returns the form error without redirecting or renewing the session', async () => {
  let count = 0
  const f = fixture(() => {
    count++
    return Promise.reject(new Error('should not renew'))
  })
  const error = f.error()
  error.config.url = '/auth/login'
  await assert.rejects(f.rejectResponse(error))
  assert.equal(count, 0)
  assert.equal(f.window.location.href, '')
  assert.equal(f.storage.get('token'), 'expired')
})

test('an old account response never retries using the current account', async () => {
  let count = 0
  const f = fixture(() => { count++; return Promise.resolve({ data: { token: 'new', refresh_token: 'new-r' } }) })
  const error = f.error()
  error.config.headers.Authorization = 'Bearer former-account'
  await assert.rejects(f.rejectResponse(error))
  assert.equal(count, 0)
  assert.equal(f.storage.get('token'), 'expired')
  assert.equal(f.retries.length, 0)
})

test('logout cannot renew or remove a newer login session', async () => {
  let count = 0
  const f = fixture(() => { count++; return Promise.reject(new Error('not called')) })
  const error = f.error()
  error.config.url = '/auth/logout'
  error.config.headers.Authorization = 'Bearer former-account'
  await assert.rejects(f.rejectResponse(error))
  assert.equal(count, 0)
  assert.equal(f.storage.get('token'), 'expired')
  assert.equal(f.window.location.href, '')
})

test('stream and Axios requests share one renewal and retry only the rejected HTTP request', async () => {
  let renewals = 0, finish
  const f = fixture(() => { renewals++; return new Promise(resolve => { finish = resolve }) })
  const sent = []
  const fetch = f.authenticatedFetch(async (_url, options) => {
    sent.push(options.headers.get('Authorization'))
    return new Response('data: [DONE]\n\n', { status: sent.length === 1 ? 401 : 200 })
  })
  const streaming = fetch('/api/v1/builder/hydrate', { method: 'POST', body: '{}' })
  await new Promise(resolve => setTimeout(resolve, 0))
  const ordinary = f.rejectResponse(f.error())
  assert.equal(renewals, 1)
  finish({ data: { token: 'renewed', refresh_token: 'renewed-refresh' } })
  assert.equal((await streaming).status, 200)
  await ordinary
  assert.deepEqual(sent, ['Bearer expired', 'Bearer renewed'])
  assert.equal(f.retries.length, 1)
  assert.deepEqual(f.events, ['ontology:session'])
})

test('a stream retry that is still unauthorized invalidates the session once without looping', async () => {
  let renewals = 0, requests = 0
  const f = fixture(async () => { renewals++; return { data: { token: 'renewed', refresh_token: 'new-refresh' } } })
  const fetch = f.authenticatedFetch(async () => { requests++; return new Response('', { status: 401 }) })
  assert.equal((await fetch('/stream')).status, 401)
  assert.equal(renewals, 1); assert.equal(requests, 2)
  assert.equal(f.storage.has('token'), false)
  assert.equal(f.window.location.href, '/login')
  assert.equal(f.events.filter(event => event === 'ontology:session').length, 2)
})

test('an aborted stream waiting for renewal does not replay its request', async () => {
  let finish, requests = 0
  const f = fixture(() => new Promise(resolve => { finish = resolve }))
  const fetch = f.authenticatedFetch(async () => { requests++; return new Response('', { status: 401 }) })
  const controller = new AbortController(), pending = fetch('/stream', { signal: controller.signal })
  await new Promise(resolve => setTimeout(resolve, 0));controller.abort()
  finish({ data: { token: 'renewed', refresh_token: 'new-refresh' } })
  await assert.rejects(pending, { name: 'AbortError' })
  assert.equal(requests, 1)
})

test('an in-flight stream renewal cannot overwrite or clear a newer account session', async () => {
  let finish, requests = 0
  const f = fixture(() => new Promise(resolve => { finish = resolve }))
  const fetch = f.authenticatedFetch(async () => { requests++; return new Response('', { status: 401 }) })
  const pending = fetch('/stream');await new Promise(resolve => setTimeout(resolve, 0))
  f.storage.set('auth_session_id', 'other-account');f.storage.set('token', 'other-token');f.storage.set('refresh_token', 'other-refresh')
  finish({ data: { token: 'former-token', refresh_token: 'former-refresh' } })
  await assert.rejects(pending, /Session changed/)
  assert.equal(requests, 1);assert.equal(f.storage.get('token'), 'other-token');assert.equal(f.window.location.href, '')
})
