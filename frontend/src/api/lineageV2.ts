import { get } from './client'
import type { LineageGraph } from '../types/lineage'

export function getLineage(params: {
  asset_id?: string
  object_type_id?: string
  depth?: number
}) {
  return get<LineageGraph>('/lineage', { params })
}
