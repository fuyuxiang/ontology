import { MarkerType, Position, type Node, type Edge } from '@vue-flow/core'
import type { GraphData } from '../types'

export interface DataLayerItem {
  entity_id: string; entity_name_cn: string; table_name: string
  field_count: number; record_count: number; datasource_name: string
}

export function useGraphLayout() {
  function transformGraphData(data: GraphData, _direction: 'LR' | 'TB' = 'LR') {
    // 按 tier 分组
    const byTier: Record<number, typeof data.nodes> = { 1: [], 2: [], 3: [] }
    for (const n of data.nodes) {
      const t = n.tier as 1 | 2 | 3
      if (byTier[t]) byTier[t].push(n)
      else byTier[3].push(n)
    }

    const NODE_W = 160
    const NODE_H = 80
    const H_GAP = 60
    const V_GAP = 120
    const TIER_Y: Record<number, number> = { 1: 0, 2: NODE_H + V_GAP, 3: (NODE_H + V_GAP) * 2 }

    const posMap = new Map<string, { x: number; y: number }>()

    for (const tier of [1, 2, 3]) {
      const group = byTier[tier]
      const totalW = group.length * NODE_W + (group.length - 1) * H_GAP
      const startX = -totalW / 2
      group.forEach((n, i) => {
        posMap.set(n.id, { x: startX + i * (NODE_W + H_GAP), y: TIER_Y[tier] })
      })
    }

    const nodes: Node[] = data.nodes.map(n => ({
      id: n.id,
      type: 'ontologyNode',
      position: posMap.get(n.id) ?? { x: 0, y: 0 },
      data: {
        name: n.name,
        nameCn: n.name_cn,
        tier: n.tier,
        status: n.status,
        relCount: n.relation_count,
        attrCount: (n as any).attr_count ?? 0,
      },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    }))

    const edges: Edge[] = data.edges.map(e => ({
      id: `${e.from_id}-${e.to_id}-${e.label}`,
      source: e.from_id,
      target: e.to_id,
      type: 'ontologyEdge',
      data: { label: e.label, cardinality: e.cardinality },
      markerEnd: MarkerType.ArrowClosed,
      animated: false,
    }))

    return { nodes, edges }
  }

  function buildDataLayerNodes(dataItems: DataLayerItem[], ontologyNodes: Node[]): { nodes: Node[]; edges: Edge[] } {
    const nodeMap = new Map(ontologyNodes.map(n => [n.id, n]))
    const nodes: Node[] = []
    const edges: Edge[] = []
    for (const item of dataItems) {
      const parent = nodeMap.get(item.entity_id)
      if (!parent) continue
      const dnId = `data-${item.entity_id}`
      nodes.push({
        id: dnId,
        type: 'dataNode',
        position: { x: parent.position.x + 20, y: parent.position.y + 110 },
        data: { ...item },
      })
      edges.push({
        id: `data-edge-${item.entity_id}`,
        source: item.entity_id,
        target: dnId,
        type: 'default',
        style: { stroke: '#94a3b8', strokeWidth: 1.2, strokeDasharray: '5,4' },
        animated: false,
      })
    }
    return { nodes, edges }
  }

  return { transformGraphData, buildDataLayerNodes }
}
