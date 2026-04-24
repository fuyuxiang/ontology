import { get } from './client'

export interface ResolvableEntity {
  entity_id: string
  entity_name: string
  entity_name_cn: string
  tier: number
  attr_count: number
  mapped_count: number
  sources: {
    table_name: string
    datasource_name: string
    datasource_id: string
    field_count: number
  }[]
}

export interface SourceField {
  attribute_id: string
  attribute_name: string
  attribute_type: string
  source_table: string
  source_field: string
  data_status: string
}

export interface SourceDataPreview {
  columns: string[]
  rows: (string | number | null)[][]
  total_rows: number
  page: number
  page_size: number
  table_name: string
  datasource_name: string
}

export interface ResolutionStats {
  entity_id: string
  total_rows: number
  distinct_identifier_rows: number | null
  null_identifier_rows: number | null
  completeness: number
}

export const resolutionApi = {
  listEntities() {
    return get<ResolvableEntity[]>('/resolution/entities')
  },

  getFields(entityId: string) {
    return get<SourceField[]>(`/resolution/entities/${entityId}/fields`)
  },

  preview(entityId: string, params?: { table_name?: string; page?: number; page_size?: number }) {
    return get<SourceDataPreview>(`/resolution/entities/${entityId}/preview`, { params })
  },

  stats(entityId: string, identifierField?: string) {
    return get<ResolutionStats>(`/resolution/entities/${entityId}/stats`, {
      params: identifierField ? { identifier_field: identifierField } : undefined,
    })
  },
}
