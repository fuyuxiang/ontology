import dagre from 'dagre'
import { MarkerType, Position, type Node, type Edge } from '@vue-flow/core'
import type { GraphData } from '../types'

const NODE_WIDTH = 180
const NODE_HEIGHT = 72

export function useGraphLayout() {
  function transformGraphData(data: GraphData, direction: 'LR' | 'TB' = 'LR') {
    const g = new dagre.graphlib.Graph()
    g.setDefaultEdgeLabel(() => ({}))
    g.setGraph({ rankdir: direction, nodesep: 60, ranksep: 120, marginx: 40, marginy: 40 })

    const nodes: Node[] = data.nodes.map(n => ({
      id: n.id,
      type: 'ontologyNode',
      position: { x: 0, y: 0 },
      data: {
        name: n.name,
        nameCn: n.name_cn,
        tier: n.tier,
        status: n.status,
        relCount: n.relation_count,
      },
      sourcePosition: direction === 'LR' ? Position.Right : Position.Bottom,
      targetPosition: direction === 'LR' ? Position.Left : Position.Top,
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

    nodes.forEach(n => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }))
    edges.forEach(e => g.setEdge(e.source, e.target))

    dagre.layout(g)

    nodes.forEach(n => {
      const pos = g.node(n.id)
      n.position = { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 }
    })

    return { nodes, edges }
  }

  return { transformGraphData }
}
