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

// 请求拦截：附加 JWT，FormData 自动处理 Content-Type
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

// token 续期状态管理
let refreshRequest: Promise<string> | null = null

// 响应拦截：401 时自动续期，续期失败才跳登录
client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const status = error.response?.status
    const isAuthRequest = /\/auth\/(?:login|refresh)(?:[?]|$)/.test(originalRequest?.url || '')

    if (status === 401 && originalRequest && !isAuthRequest && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token')

      if (!refreshToken) {
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(error)
      }

      originalRequest._retry = true
      try {
        if (!refreshRequest) {
          refreshRequest = axios
            .post(`${baseURL}/auth/refresh`, { refresh_token: refreshToken })
            .then((resp) => {
              const { token: newToken, refresh_token: newRefresh } = resp.data
              localStorage.setItem('token', newToken)
              localStorage.setItem('refresh_token', newRefresh)
              return newToken as string
            })
            .finally(() => {
              refreshRequest = null
            })
        }
        const newToken = await refreshRequest
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return client(originalRequest)
      } catch {
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
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
