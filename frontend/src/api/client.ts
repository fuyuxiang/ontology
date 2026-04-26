import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const client: AxiosInstance = axios.create({
  baseURL,
  timeout: 15000,
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

// 响应拦截：统一错误处理
client.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// 泛型请求封装
export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res: AxiosResponse<T> = await client.get(url, config)
  return res.data
}

export async function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
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
