import { MarkerType, Position, type Edge, type Node } from '@vue-flow/core'
import type { EntityListItem, GraphData, Tier } from '../types'

interface LayoutNode {
  id: string
  tier: Tier
  relationCount: number
}

type LayoutDirection = 'LR' | 'TB'

function compareNodes(a: LayoutNode, b: LayoutNode) {
  if (a.tier !== b.tier) return a.tier - b.tier
  if (a.relationCount !== b.relationCount) return b.relationCount - a.relationCount
  return a.id.localeCompare(b.id)
}

function resolvePortPositions(direction: LayoutDirection) {
  return direction === 'TB'
    ? { sourcePosition: Position.Bottom, targetPosition: Position.Top }
    : { sourcePosition: Position.Right, targetPosition: Position.Left }
}

function createTieredPositions(nodes: LayoutNode[], direction: LayoutDirection) {
  const positions = new Map<string, { x: number; y: number }>()
  const sorted = [...nodes].sort(compareNodes)
  const buckets = {
    1: sorted.filter(node => node.tier === 1),
    2: sorted.filter(node => node.tier === 2),
    3: sorted.filter(node => node.tier === 3),
  } satisfies Record<Tier, LayoutNode[]>

  if (direction === 'TB') {
    const laneY: Record<Tier, number> = { 1: -280, 2: 0, 3: 280 }
    const perRow = 4
    const columnGap = 250
    const rowGap = 176

    ;([1, 2, 3] as Tier[]).forEach(tier => {
      const laneNodes = buckets[tier]
      const rowCount = Math.max(1, Math.ceil(laneNodes.length / perRow))
      const visibleColumnCount = Math.min(perRow, Math.max(1, laneNodes.length))

      laneNodes.forEach((node, index) => {
        const row = Math.floor(index / perRow)
        const column = index % perRow
        const centeredColumn = column - (visibleColumnCount - 1) / 2
        const centeredRow = row - (rowCount - 1) / 2

        positions.set(node.id, {
          x: centeredColumn * columnGap + (row % 2 === 1 ? 38 : 0),
          y: laneY[tier] + centeredRow * rowGap,
        })
      })
    })

    return positions
  }

  const laneX: Record<Tier, number> = { 1: -500, 2: 0, 3: 500 }
  const perColumn = 5
  const columnGap = 240
  const rowGap = 168

  ;([1, 2, 3] as Tier[]).forEach(tier => {
    const laneNodes = buckets[tier]
    const columnCount = Math.max(1, Math.ceil(laneNodes.length / perColumn))
    const visibleRowCount = Math.min(perColumn, Math.max(1, laneNodes.length))

    laneNodes.forEach((node, index) => {
      const column = Math.floor(index / perColumn)
      const row = index % perColumn
      const centeredColumn = column - (columnCount - 1) / 2
      const centeredRow = row - (visibleRowCount - 1) / 2

      positions.set(node.id, {
        x: laneX[tier] + centeredColumn * columnGap,
        y: centeredRow * rowGap + (column % 2 === 1 ? 34 : 0),
      })
    })
  })

  return positions
}

export interface DataLayerItem {
  entity_id: string; entity_name_cn: string; table_name: string
  field_count: number; record_count: number; datasource_name: string
}

export function useGraphLayout() {
  const lanePositions = {
    LR: { 1: -500, 2: 0, 3: 500 } as Record<Tier, number>,
    TB: { 1: -280, 2: 0, 3: 280 } as Record<Tier, number>,
  }

  function transformGraphData(
    data: GraphData,
    direction: LayoutDirection = 'LR',
    entityMeta = new Map<string, EntityListItem>(),
  ) {
    const layoutNodes: LayoutNode[] = data.nodes.map(node => ({
      id: node.id,
      tier: node.tier,
      relationCount: node.relation_count,
    }))

    const positions = createTieredPositions(layoutNodes, direction)
    const { sourcePosition, targetPosition } = resolvePortPositions(direction)

    const nodes: Node[] = data.nodes.map(node => {
      const meta = entityMeta.get(node.id)

      return {
        id: node.id,
        type: 'ontologyNode',
        position: positions.get(node.id) ?? { x: 0, y: 0 },
        data: {
          name: meta?.name ?? node.name,
          nameCn: meta?.name_cn ?? node.name_cn,
          tier: node.tier,
          status: meta?.status ?? node.status,
          relCount: node.relation_count,
          attrCount: meta?.attr_count ?? 0,
          ruleCount: meta?.rule_count ?? 0,
          datasource: meta?.datasource_name ?? null,
        },
        sourcePosition,
        targetPosition,
      }
    })

    const edges: Edge[] = data.edges.map(edge => ({
      id: `${edge.from_id}-${edge.to_id}-${edge.label}`,
      source: edge.from_id,
      target: edge.to_id,
      type: 'ontologyEdge',
      data: { label: edge.label, cardinality: edge.cardinality },
      markerEnd: MarkerType.ArrowClosed,
      animated: false,
    }))

    return { nodes, edges }
  }

  return { transformGraphData, lanePositions }
}
