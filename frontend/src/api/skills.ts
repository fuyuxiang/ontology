import { productText } from '../composables/useProductText'
import { get, post, put, del } from './client'

export interface SkillToolRef {
  type: 'function' | 'action'
  id: string
}
export interface SkillTestCase {
  id: string
  name: string
  input: string | Record<string, unknown>
  expected_keywords: string[]
  expected_tools: string[]
}
export interface SkillItem {
  id: string
  name: string
  description: string
  prompt_template: string
  input_schema: Record<string, unknown>
  output_schema: Record<string, unknown>
  tools: SkillToolRef[]
  test_cases: SkillTestCase[]
  asset_refs: string[]
  ontology_id: string | null
  ontology_version_id: string | null
  entity_ids: string[]
  applicable_tasks: string
  excluded_tasks: string
  owner_team: string
  visibility: 'private' | 'workspace'
  tags: string[]
  status: 'draft' | 'active' | 'archived'
  current_version: number
  has_changes: boolean
  ref_count: number
  can_edit: boolean
  created_at?: string
  updated_at?: string
  ontology_name?: string | null
  referenced_ontology_ids?: string[]
}
export interface SkillVersion {
  id?: string
  version: number
  description?: string
  created_at?: string
  snapshot?: SkillItem
  definition?: SkillItem
  snapshot_json?: SkillItem
}
export interface SkillCatalogItem {
  id: string
  name: string
  name_cn?: string
  display_name?: string
  description?: string
  status?: string
  ontology_id?: string | null
  version?: string | number
  [key: string]: unknown
}
export interface SkillCatalog {
  ontologies?: Array<{ id: string; code: string; name: string }>
  ontology_versions: SkillCatalogItem[]
  entities: SkillCatalogItem[]
  functions: SkillCatalogItem[]
  actions: SkillCatalogItem[]
  assets: SkillCatalogItem[]
}
export interface SkillValidation {
  valid?: boolean
  ok?: boolean
  errors: Array<string | { field?: string; message: string }>
  warnings: Array<string | { field?: string; message: string }>
  fingerprint?: string
  dependencies?: Record<string, unknown>
}
export interface SkillReference {
  id?: string
  agent_id?: string
  agent_name?: string
  name?: string
  version?: number
  skill_version?: number
  status?: string
  source?: 'draft' | 'published'
  agent_version?: number
  has_update?: boolean
  [key: string]: unknown
}
export interface SkillTestRun {
  id: string
  created_at?: string
  status?: string
  passed?: boolean
  summary?: string
  results?: Array<Record<string, unknown>>
  validation_level?: 'runtime' | 'static'
  case_results?: Array<{
    id: string
    name: string
    passed: boolean
    answer?: string
    errors?: string[]
    tool_runs?: Array<Record<string, unknown>>
  }>
  errors?: string[]
  fingerprint?: string
  [key: string]: unknown
}

export const skillsApi = {
  list: (params?: { ontology_id?: string; status?: string; search?: string }) =>
    get<SkillItem[]>('/skills', { params }),
  get: (id: string) => get<SkillItem>(`/skills/${id}`),
  create: (data: Partial<SkillItem>) => post<SkillItem>('/skills', data),
  update: (id: string, data: Partial<SkillItem>) => put<SkillItem>(`/skills/${id}`, data),
  delete: (id: string) => del<void>(`/skills/${id}`),
  versions: (id: string) => get<SkillVersion[]>(`/skills/${id}/versions`),
  version: (id: string, version: number) => get<SkillVersion>(`/skills/${id}/versions/${version}`),
  catalog: (ontologyId?: string, ontologyVersionId?: string) =>
    get<SkillCatalog>('/skills/catalog', {
      params: { ontology_id: ontologyId, ontology_version_id: ontologyVersionId },
    }),
  validate: (id: string) => post<SkillValidation>(`/skills/${id}/validate`),
  test: (id: string, data?: { test_case_ids?: string[] }) =>
    post<SkillTestRun>(`/skills/${id}/test`, data || {}, { timeout: 600000 }),
  publish: (id: string, description: string) =>
    post<SkillItem>(`/skills/${id}/publish`, { description }),
  archive: (id: string) => post<SkillItem>(`/skills/${id}/archive`),
  restore: (id: string) => post<SkillItem>(`/skills/${id}/restore`),
  references: (id: string) => get<SkillReference[]>(`/skills/${id}/references`),
  testRuns: (id: string) => get<SkillTestRun[]>(`/skills/${id}/test-runs`),
}

export function skillError(error: unknown, fallback = '操作失败，请稍后重试'): string {
  const err = error as { response?: { status?: number; data?: { detail?: unknown } }; message?: string }
  if (err.response?.status === 403) return productText('当前账号没有执行此操作的权限，请联系管理员配置相应权限。')
  const detail = err.response?.data?.detail
  if (typeof detail === 'string') return productText(detail)
  if (Array.isArray(detail))
    return detail.map((item) => item.msg || item.message || String(item)).join('；')
  if (detail && typeof detail === 'object' && 'message' in detail) {
    const errors =
      'errors' in detail && Array.isArray(detail.errors) ? detail.errors.map(String).join('；') : ''
    return `${String(detail.message)}${errors ? `：${errors}` : ''}`
  }
  return productText(err.message || fallback)
}
