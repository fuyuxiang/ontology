import { get } from './client'

export interface VersionFunction {
  id: string
  name: string
  description: string
  return_type: string
  input_schema: Array<{ name: string; type: string; version_attribute_id: string; required: boolean }>
  version_entity_id: string
  callable_name: string
}

export interface VersionRule {
  id: string
  name: string
  description: string
  condition_expr: string
  priority: string
  input_params: Array<{ name: string; type: string; version_attribute_id: string; required: boolean }>
  version_entity_id: string
}

export interface VersionAction {
  id: string
  name: string
  description: string
  category: string
  action_type: string
  parameters_json: Array<{ name: string; type: string; version_attribute_id: string; required: boolean }>
  version_entity_id: string
}

export interface ImpactAnalysis {
  published_versions: string[]
  referencing_workflows: Array<{ id: string; name: string; version: string }>
  referencing_skills: Array<{ id: string; name: string; version: string }>
  safe_to_delete: boolean
  message: string
}

export function fetchVersionFunctions(versionId: string) {
  return get<VersionFunction[]>(`/ontology-publish/versions/${versionId}/functions`)
}

export function fetchVersionRules(versionId: string) {
  return get<VersionRule[]>(`/ontology-publish/versions/${versionId}/rules`)
}

export function fetchVersionActions(versionId: string) {
  return get<VersionAction[]>(`/ontology-publish/versions/${versionId}/actions`)
}

export function fetchImpactAnalysis(type: 'functions' | 'rules' | 'actions', id: string) {
  return get<ImpactAnalysis>(`/impact-analysis/${type}/${id}`)
}
