import { get, post, put, del } from './client'
import type { OntologyEntity, EntityListItem, EntityRelationDetail, GraphData, Tier, EntityStatus, FileImportResult } from '../types'

export interface EntityQuery {
  tier?: Tier
  status?: EntityStatus
  search?: string
  namespace?: string
  ontology_id?: string
}

// ── 本体文件预览（只解析不落库）──
export interface PreviewProperty {
  name: string
  display_name: string
  type: string
  raw_type: string
  required: boolean
  description: string
  source_table: string | null
  source_field: string | null
}
export interface PreviewObject {
  name: string
  display_name: string
  tier: number
  namespace: string | null
  primary_key: string | null
  description: string
  properties: PreviewProperty[]
}
export interface PreviewRelation {
  name: string
  display_name: string
  source: string
  target: string
  cardinality: string
  description: string
}
export interface PreviewAction {
  name: string
  display_name: string
  trigger: string
  target_object: string | null
  description: string
}
export interface PreviewDataSource {
  source_id: string
  physical_table: string
  display_name: string
}
export interface OntologyPreviewResult {
  objects: PreviewObject[]
  relations: PreviewRelation[]
  actions: PreviewAction[]
  data_sources: PreviewDataSource[]
  summary: {
    object_count: number
    relation_count: number
    property_count: number
    action_count: number
  }
}

export const entityApi = {
  list(query?: EntityQuery) {
    return get<EntityListItem[]>('/entities', { params: query })
  },

  detail(id: string) {
    return get<OntologyEntity>(`/entities/${id}`)
  },

  create(data: Partial<OntologyEntity>) {
    return post<OntologyEntity>('/entities', data)
  },

  update(id: string, data: Partial<OntologyEntity>) {
    return put<OntologyEntity>(`/entities/${id}`, data)
  },

  remove(id: string, force = false) {
    return del<void>(`/entities/${id}${force ? '?force=true' : ''}`)
  },

  graph(id: string, depth = 2, direction: 'both' | 'outgoing' | 'incoming' = 'both') {
    return get<GraphData>(`/entities/${id}/graph`, { params: { depth, direction } })
  },

  lineage(id: string, depth = 2) {
    return get<GraphData>(`/entities/${id}/lineage`, { params: { depth } })
  },

  graphAll() {
    return get<GraphData>('/entities/graph')
  },

  relations(entityId: string, ontologyId?: string) {
    const params: Record<string, string> = { entity_id: entityId }
    if (ontologyId) params.ontology_id = ontologyId
    return get<EntityRelationDetail[]>('/relations', { params })
  },

  search(keyword: string) {
    return get<EntityListItem[]>('/entities', { params: { search: keyword } })
  },

  createFromDatasource(data: { datasource_id: string; table_name: string; name_cn: string; tier: number; namespace?: string }) {
    return post<OntologyEntity>('/entities/from-datasource', data)
  },

  sceneLayerStats(namespace: string) {
    return get<{ key: string; label: string; entityCount: number; attrCount: number; relationCount: number; actionCount: number }[]>(
      '/entities/scene-layer-stats', { params: { namespace } },
    )
  },

  importFromFile(file: File, fileType: string, namespace?: string, ontologyId?: string) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', fileType)
    if (namespace) formData.append('namespace', namespace)
    if (ontologyId) formData.append('ontology_id', ontologyId)
    return post<FileImportResult>('/entities/from-file', formData)
  },

  previewFile(file: File, fileType: string, namespace?: string) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', fileType)
    if (namespace) formData.append('namespace', namespace)
    return post<OntologyPreviewResult>('/entities/preview-file', formData)
  },

  dataLayer() {
    return get<{ entity_id: string; entity_name_cn: string; table_name: string; field_count: number; record_count: number; datasource_name: string }[]>('/entities/data-layer')
  },

  updateAttributeMappings(entityId: string, items: { attribute_id: string; source_table: string | null; source_field: string | null; data_status: string }[]) {
    return put<OntologyEntity>(`/entities/${entityId}/attribute-mappings`, items)
  },

  deleteAttribute(entityId: string, attributeId: string, force = false) {
    return del<void>(`/entities/${entityId}/attributes/${attributeId}`, { params: { force } })
  },
}
