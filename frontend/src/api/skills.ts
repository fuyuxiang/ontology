import client from './client'

export interface SkillItem {
  id: string
  name: string
  description: string
  skill_type: string
  config_json: Record<string, any>
  code_ref: string
  status: string
  current_version: number
  input_schema: Record<string, any> | null
  output_schema: Record<string, any> | null
  prompt_template: string
  tools: any[] | null
  test_cases: any[] | null
  asset_refs: Record<string, any> | null
  created_by: string
  reviewed_by: string
  created_at: string
  updated_at: string
}

export interface VersionItem {
  id: string
  version: number
  change_log: string
  published_by: string
  published_at: string
}

export const skillsApi = {
  list: (status?: string) => client.get<SkillItem[]>('/skills', { params: status ? { status } : {} }).then(r => r.data),
  get: (id: string) => client.get<SkillItem>(`/skills/${id}`).then(r => r.data),
  create: (data: Partial<SkillItem>) => client.post<SkillItem>('/skills', data).then(r => r.data),
  update: (id: string, data: Partial<SkillItem>) => client.put<SkillItem>(`/skills/${id}`, data).then(r => r.data),
  delete: (id: string) => client.delete(`/skills/${id}`).then(r => r.data),
  versions: (id: string) => client.get<VersionItem[]>(`/skills/${id}/versions`).then(r => r.data),
  rollback: (id: string, targetVersion: number) => client.post(`/skills/${id}/rollback`, { target_version: targetVersion }).then(r => r.data),
  deprecate: (id: string) => client.post(`/skills/${id}/deprecate`).then(r => r.data),
}
