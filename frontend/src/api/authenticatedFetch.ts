import { captureAuthSession, invalidateAuthSession, refreshAccessToken } from './client'

/** A 401 before a stream begins is safe to retry once; stream failures are never replayed. */
export async function authenticatedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const session = captureAuthSession()
  const headers = new Headers(init.headers)
  if (session.token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${session.token}`)
  const response = await fetch(input, { ...init, headers })
  if (response.status !== 401) return response
  if (headers.get('Authorization') !== `Bearer ${session.token}` || captureAuthSession().id !== session.id) return response
  if (init.signal?.aborted) return response
  const token = await refreshAccessToken(session)
  init.signal?.throwIfAborted()
  await response.body?.cancel().catch(() => undefined)
  headers.set('Authorization', `Bearer ${token}`)
  const retry = await fetch(input, { ...init, headers })
  if (retry.status === 401) invalidateAuthSession(session)
  return retry
}
