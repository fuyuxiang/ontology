import { get, post, put, del } from './client'
import type { OntologyEntity, EntityListItem, GraphData, Tier, EntityStatus } from '../types'

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
}
