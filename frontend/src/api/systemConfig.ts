import { get, put, post } from './client'

export interface ConfigItem {
  key: string
  value: string | null
  description: string | null
  is_sensitive: boolean
}

export interface ConfigResponse {
  groups: Record<string, ConfigItem[]>
}

export interface TestResult {
  success: boolean
  message: string
}

export const systemConfigApi = {
  /** 获取全部配置（按分组） */
  getAll() {
    return get<ConfigResponse>('/system-config')
  },

  /** 保存某组配置 */
  save(group: string, items: { key: string; value: string | null }[]) {
    return put<{ message: string }>('/system-config', { group, items })
  },

  /** 测试 AI 连通性 */
  testAi() {
    return post<TestResult>('/system-config/test-ai')
  },

  /** 测试邮件发送 */
  testEmail(recipient: string) {
    return post<TestResult>('/system-config/test-email', { recipient })
  },
}
