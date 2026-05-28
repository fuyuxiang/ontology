import { get } from './client'

export type LineageNodeKind = 'asset' | 'object_type' | 'action' | 'rule'

export interface LineageNode {
  kind: LineageNodeKind
  id: string
  label: string | null
  sub_label: string | null
  extra: Record<string, unknown> | null
}

export interface LineageEdge {
  source: { kind: LineageNodeKind; id: string }
  target: { kind: LineageNodeKind; id: string }
  relation: string
  via_module: string | null
  via_purpose: string | null
  weight: number
}

export interface LineageGraph {
  nodes: LineageNode[]
  edges: LineageEdge[]
}

export const lineageApi = {
  overview() {
    return get<LineageGraph>('/lineage/overview')
  },
  forAsset(assetId: string, depth = 2) {
    return get<LineageGraph>(`/lineage?asset_id=${encodeURIComponent(assetId)}&depth=${depth}`)
  },
  forObjectType(objectTypeId: string, depth = 2) {
    return get<LineageGraph>(`/lineage?object_type_id=${encodeURIComponent(objectTypeId)}&depth=${depth}`)
  },
}
