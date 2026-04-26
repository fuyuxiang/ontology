import client from './client'

export interface SkillItem {
  id: string
  name: string
  description: string
  skill_type: string
  config_json: Record<string, any>
  code_ref: string
  status: string
  created_at: string
  updated_at: string
}

export const skillsApi = {
  list: () => client.get<SkillItem[]>('/skills').then(r => r.data),
  get: (id: string) => client.get<SkillItem>(`/skills/${id}`).then(r => r.data),
  create: (data: Partial<SkillItem>) => client.post<SkillItem>('/skills', data).then(r => r.data),
  update: (id: string, data: Partial<SkillItem>) => client.put<SkillItem>(`/skills/${id}`, data).then(r => r.data),
  delete: (id: string) => client.delete(`/skills/${id}`).then(r => r.data),
}
