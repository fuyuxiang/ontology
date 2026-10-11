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
  const window = { location: { href: '' } }
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
  return { rejectResponse, retries, storage, window, error }
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
