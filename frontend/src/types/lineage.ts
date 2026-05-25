// 本体侧血缘：Asset → ObjectType → Action

export type LineageNodeKind = 'asset' | 'object_type' | 'action' | 'rule'
export type LineageRelation = 'binds_to' | 'reads' | 'writes' | 'derives_from'

export interface LineageNode {
  kind: LineageNodeKind
  id: string
}

export interface LineageEdgeOut {
  source: LineageNode
  target: LineageNode
  relation: LineageRelation
  via_module?: string | null
  via_purpose?: string | null
  weight: number
}

export interface LineageGraph {
  nodes: LineageNode[]
  edges: LineageEdgeOut[]
}
