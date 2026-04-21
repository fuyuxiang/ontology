import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force'
import { MarkerType, Position, type Node, type Edge } from '@vue-flow/core'
import type { GraphData } from '../types'

interface SimNode { id: string; x: number; y: number; tier: number }
interface SimLink { source: string; target: string }

export function useGraphLayout() {
  function transformGraphData(data: GraphData, _direction: 'LR' | 'TB' = 'LR') {
    const simNodes: SimNode[] = data.nodes.map(n => ({
      id: n.id, x: Math.random() * 800, y: Math.random() * 600, tier: n.tier,
    }))

    const simLinks: SimLink[] = data.edges.map(e => ({
      source: e.from_id, target: e.to_id,
    }))

    const nodeCount = simNodes.length
    const strength = nodeCount > 30 ? -600 : nodeCount > 15 ? -400 : -300

    const sim = forceSimulation(simNodes as any)
      .force('link', forceLink(simLinks as any).id((d: any) => d.id).distance(180).strength(0.4))
      .force('charge', forceManyBody().strength(strength))
      .force('center', forceCenter(0, 0))
      .force('collide', forceCollide(90))
      .stop()

    for (let i = 0; i < 300; i++) sim.tick()

    const nodes: Node[] = data.nodes.map((n, i) => ({
      id: n.id,
      type: 'ontologyNode',
      position: { x: (simNodes[i] as any).x, y: (simNodes[i] as any).y },
      data: {
        name: n.name,
        nameCn: n.name_cn,
        tier: n.tier,
        status: n.status,
        relCount: n.relation_count,
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

  return { transformGraphData }
}
