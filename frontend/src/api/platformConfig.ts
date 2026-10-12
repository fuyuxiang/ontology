import { get } from './client'

export interface PlatformConfig {
  system_name: string
  language: 'zh-CN' | 'en'
  timezone: 'Asia/Shanghai' | 'UTC'
}

/** Anonymous, safe branding/preferences; contains no credentials or auth policy. */
export const platformConfigApi = {
  get: () => get<PlatformConfig>('/auth/platform-config'),
}
