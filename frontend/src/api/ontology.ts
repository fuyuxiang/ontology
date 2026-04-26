import { get, post, put, del } from './client'
import type { OntologyEntity, EntityListItem, GraphData, Tier, EntityStatus, FileImportResult } from '../types'

export interface EntityQuery {
  tier?: Tier
  status?: EntityStatus
  search?: string
  namespace?: string
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

  remove(id: string) {
    return del<void>(`/entities/${id}`)
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

  search(keyword: string) {
    return get<EntityListItem[]>('/entities', { params: { search: keyword } })
  },

  createFromDatasource(data: { datasource_id: string; table_name: string; name_cn: string; tier: number; namespace?: string }) {
    return post<OntologyEntity>('/entities/from-datasource', data)
  },

  sceneLayerStats(namespace: string) {
    return get<{ key: string; label: string; entityCount: number; attrCount: number; relationCount: number; ruleCount: number; actionCount: number }[]>(
      '/entities/scene-layer-stats', { params: { namespace } },
    )
  },

  importFromFile(file: File, fileType: string, namespace?: string) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', fileType)
    if (namespace) formData.append('namespace', namespace)
    return post<FileImportResult>('/entities/from-file', formData)
  },

  dataLayer() {
    return get<{ entity_id: string; entity_name_cn: string; table_name: string; field_count: number; record_count: number; datasource_name: string }[]>('/entities/data-layer')
  },

  updateAttributeMappings(entityId: string, items: { attribute_id: string; source_table: string | null; source_field: string | null; data_status: string }[]) {
    return put<OntologyEntity>(`/entities/${entityId}/attribute-mappings`, items)
  },
}
