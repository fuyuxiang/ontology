import { get, post } from './client'

export interface AssetTreeColumn {
  name: string
  type: string
  comment: string
  is_pk: boolean
}

export interface AssetTreeTable {
  asset_id: string
  table_name: string
  columns: AssetTreeColumn[]
}

export interface AssetTreeNode {
  connection_id: string | null
  connection_name: string
  db_type: string | null
  database: string | null
  tables: AssetTreeTable[]
}

export interface ColumnCandidate {
  column: string
  column_type: string | null
  comment: string | null
  score: number
  tier: 'high' | 'medium' | 'low'
  reason: string
}

export interface PropertySuggestion {
  property_name: string
  candidates: ColumnCandidate[]
}

export function fetchAssetTree(connectionId?: string): Promise<{ tree: AssetTreeNode[] }> {
  const params = connectionId ? { connection_id: connectionId } : {}
  return get<{ tree: AssetTreeNode[] }>('/assets/tree', { params })
}

export function suggestColumns(
  assetId: string,
  properties: { name: string; type?: string; description?: string }[],
): Promise<{ suggestions: PropertySuggestion[] }> {
  return post<{ suggestions: PropertySuggestion[] }>('/builder/suggest-columns', {
    asset_id: assetId,
    properties,
  })
}
