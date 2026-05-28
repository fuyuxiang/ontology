import { get, post } from './client'

export interface MappingCandidate {
  column: string
  column_type: string | null
  column_comment: string | null
  is_pk: boolean
  score: number
  tier: 'high' | 'medium' | 'low' | 'none'
  reason: string
  source: 'heuristic' | 'llm'
}

export interface MappingSuggestionRow {
  attribute_id: string
  attribute_name: string
  attribute_type: string
  attribute_description: string
  candidates: MappingCandidate[]
}

export interface MappingSuggestResponse {
  object_type: { id: string; name: string; name_cn: string }
  asset: { id: string; name: string; kind: string; table: string | null }
  coverage: { total: number; high: number; medium: number; low: number; none: number }
  suggestions: MappingSuggestionRow[]
}

export interface FieldMappingPayload {
  attribute_id: string
  source_column: string
  transform?: string | null
}

export interface ApplyResponse {
  action: 'created' | 'updated'
  binding_id: string
  field_mappings_count: number
}

export interface AssetSuggestionRow {
  asset: {
    id: string; name: string; kind: string; table: string | null
    domain: string | null; connection_id: string | null
  }
  coverage: { high: number; medium: number; low: number; none: number; total: number }
  rank_score: number
  top_attrs: { attribute_name: string; column: string; tier: 'high' | 'medium' | 'low'; score: number }[]
  already_bound_role: string | null
}

export interface SuggestAssetsResponse {
  object_type: { id: string; name: string; name_cn: string }
  total_attrs: number
  existing_bindings: { binding_id: string; asset_id: string; role: string; field_count: number }[]
  asset_suggestions: AssetSuggestionRow[]
  combo: { primary: string | null; enrichments: string[]; covered_attrs: number }
}

export interface CoverageRow {
  object_type_id: string
  total: number
  mapped: number
}

export const mappingApi = {
  suggestAssets(object_type_id: string) {
    return post<SuggestAssetsResponse>('/mapping/suggest_assets', { object_type_id })
  },
  coverage() {
    return get<CoverageRow[]>('/mapping/coverage')
  },
  suggest(body: { object_type_id: string; asset_id: string; use_llm?: boolean; top_k?: number }) {
    return post<MappingSuggestResponse>('/mapping/suggest', body)
  },
  apply(body: {
    object_type_id: string
    asset_id: string
    field_mappings: FieldMappingPayload[]
    id_column?: string | null
    filter_expr?: string | null
    role?: string
  }) {
    return post<ApplyResponse>('/mapping/apply', body)
  },
}
