import { MarkerType, Position, type Node, type Edge } from '@vue-flow/core'
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force'
import type { GraphData } from '../types'

export interface DataLayerItem {
  entity_id: string; entity_name_cn: string; table_name: string
  field_count: number; record_count: number; datasource_name: string
}

interface SimNode {
  id: string
  x: number
  y: number
  tier: number
}

interface SimLink {
  source: string
  target: string
}

export function useGraphLayout() {
  function transformGraphData(data: GraphData, _direction: 'LR' | 'TB' = 'LR') {
    const simNodes: SimNode[] = data.nodes.map(n => ({
      id: n.id,
      x: (Math.random() - 0.5) * 400,
      y: (Math.random() - 0.5) * 400,
      tier: n.tier as number,
    }))

    const simLinks: SimLink[] = data.edges.map(e => ({
      source: e.from_id,
      target: e.to_id,
    }))

    const simulation = forceSimulation(simNodes as any)
      .force('link', forceLink(simLinks as any).id((d: any) => d.id).distance(160))
      .force('charge', forceManyBody().strength(-500))
      .force('center', forceCenter(0, 0))
      .force('collide', forceCollide(60))
      .stop()

    for (let i = 0; i < 200; i++) simulation.tick()

    const posMap = new Map<string, { x: number; y: number }>()
    for (const n of simNodes) {
      posMap.set(n.id, { x: n.x, y: n.y })
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
        actionCount: (n as any).action_count ?? 0,
        ruleCount: (n as any).rule_count ?? 0,
        functionCount: (n as any).function_count ?? 0,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
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
        position: { x: parent.position.x + 20, y: parent.position.y + 100 },
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
