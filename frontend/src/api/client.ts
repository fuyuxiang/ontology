import axios from 'axios'
import type {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const client: AxiosInstance = axios.create({
  baseURL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

export interface AuthSession { id: string | null; token: string | null; refreshToken: string | null }
const SESSION_KEY = 'auth_session_id'
export function captureAuthSession(): AuthSession {
  const token = localStorage.getItem('token')
  let id = localStorage.getItem(SESSION_KEY)
  if (token && !id) {
    id = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`
    localStorage.setItem(SESSION_KEY, id)
  }
  return { id, token, refreshToken: localStorage.getItem('refresh_token') }
}

export function invalidateAuthSession(session: AuthSession) {
  if (captureAuthSession().id !== session.id) return
  localStorage.removeItem('token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem(SESSION_KEY)
  notifySession()
  window.location.href = '/login'
}

let refreshRequest: { id: string | null; promise: Promise<string> } | null = null
export async function refreshAccessToken(session: AuthSession): Promise<string> {
  const current = captureAuthSession()
  if (!session.id || current.id !== session.id) throw new Error('Session changed')
  // Another HTTP or streaming request may already have renewed this session.
  if (current.token && current.token !== session.token) return current.token
  if (!current.refreshToken) {
    invalidateAuthSession(session)
    throw new Error('Session expired')
  }
  if (!refreshRequest || refreshRequest.id !== session.id) {
    const refreshToken = current.refreshToken
    const pending = { id: session.id, promise: Promise.resolve('') }
    pending.promise = axios.post(`${baseURL}/auth/refresh`, { refresh_token: refreshToken })
      .then(resp => {
        const latest = captureAuthSession()
        if (latest.id !== session.id || latest.refreshToken !== refreshToken) throw new Error('Session changed while refreshing')
        const { token, refresh_token } = resp.data
        if (typeof token !== 'string' || !token || typeof refresh_token !== 'string' || !refresh_token) throw new Error('Invalid refresh response')
        localStorage.setItem('token', token)
        localStorage.setItem('refresh_token', refresh_token)
        notifySession()
        return token
      })
      .catch(error => { invalidateAuthSession(session); throw error })
      .finally(() => { if (refreshRequest === pending) refreshRequest = null })
    refreshRequest = pending
  }
  const token = await refreshRequest.promise
  if (captureAuthSession().id !== session.id || localStorage.getItem('token') !== token) throw new Error('Session changed')
  return token
}

type SessionRequest = InternalAxiosRequestConfig & { _retry?: boolean; _authSession?: AuthSession }

// 请求拦截：附加 JWT，FormData 自动处理 Content-Type
client.interceptors.request.use((config) => {
  const request = config as SessionRequest
  request._authSession ||= captureAuthSession()
  const token = localStorage.getItem('token')
  if (token && config.headers && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

function notifySession() {
  if (window.dispatchEvent) window.dispatchEvent(new Event('ontology:session'))
}

// 响应拦截：401 时自动续期，续期失败才跳登录
client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config as SessionRequest
    const status = error.response?.status
    const isAuthRequest = /\/auth\/(?:login|refresh|logout|sso\/exchange)(?:[?]|$)/.test(originalRequest?.url || '')

    if (status === 401 && originalRequest && !isAuthRequest) {
      // A request from a previous account must never be retried as the new account.
      const sentAuthorization = originalRequest.headers?.Authorization
      const currentToken = localStorage.getItem('token')
      const session = originalRequest._authSession || captureAuthSession()
      if (session.id !== captureAuthSession().id || (!originalRequest._authSession && sentAuthorization && sentAuthorization !== `Bearer ${currentToken}`)) {
        return Promise.reject(error)
      }
      if (originalRequest._retry) {
        invalidateAuthSession(session)
        return Promise.reject(error)
      }
      originalRequest._retry = true
      try {
        const newToken = await refreshAccessToken(session)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return client(originalRequest)
      } catch {
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)

// 泛型请求封装
export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res: AxiosResponse<T> = await client.get(url, config)
  return res.data
}

export async function post<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const res: AxiosResponse<T> = await client.post(url, data, config)
  return res.data
}

export async function put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const res: AxiosResponse<T> = await client.put(url, data, config)
  return res.data
}

export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res: AxiosResponse<T> = await client.delete(url, config)
  return res.data
}

export default client
