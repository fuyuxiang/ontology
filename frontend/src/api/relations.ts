import { get, post, del } from './client'

export interface RelationData {
  id: string
  from_entity_id: string
  from_entity_name: string
  to_entity_id: string
  to_entity_name: string
  name: string
  rel_type: string
  cardinality: string
  description: string | null
}

export interface RelationCreate {
  from_entity_id: string
  to_entity_id: string
  name: string
  rel_type?: string
  cardinality?: string
  description?: string
}

export const relationApi = {
  list(entityId?: string) {
    return get<RelationData[]>('/relations', { params: entityId ? { entity_id: entityId } : {} })
  },
  create(data: RelationCreate) {
    return post<RelationData>('/relations', data)
  },
  remove(id: string) {
    return del<void>(`/relations/${id}`)
  },
}
