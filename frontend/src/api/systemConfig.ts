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

// ── AI 模型类型 ──

export interface AiModel {
  id: string
  name: string
  provider: string
  model_id: string
  api_key: string
  base_url: string
  temperature: number
  max_tokens: number
  scenes: string[]
  is_default: boolean
}

export interface ModelScene {
  key: string
  label: string
  desc: string
}

export interface AiModelsResponse {
  models: AiModel[]
  scenes: ModelScene[]
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

  // ── AI 模型管理 ──

  /** 获取 AI 模型列表 */
  getAiModels() {
    return get<AiModelsResponse>('/system-config/ai/models')
  },

  /** 保存 AI 模型列表 */
  saveAiModels(models: AiModel[]) {
    return put<{ message: string }>('/system-config/ai/models', { models })
  },

  /** 测试指定模型连通性 */
  testAiModel(data: { api_key: string; base_url: string; model_id: string }) {
    return post<TestResult>('/system-config/ai/models/test', data)
  },

  /** 获取模型使用场景列表 */
  getModelScenes() {
    return get<ModelScene[]>('/system-config/scenes')
  },
}
