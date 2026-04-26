import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'

export type NodeType = 'datasource' | 'operator' | 'model'

export interface G6NodeData {
  id: string
  data: {
    label: string
    subLabel: string
    nodeType: NodeType
    tier: number
    status: string
    relationCount: number
    ruleCount: number
    attrCount: number
    actionCount: number
  }
}

export interface G6EdgeData {
  id: string
  source: string
  target: string
  data: {
    label: string
    cardinality: string
  }
}

function classifyNode(e: EntityListItem): NodeType {
  const n = (e.name || '').toLowerCase()
  if (e.tier === 1 || /subscriber|user|customer|billing|contract/.test(n)) return 'datasource'
  if (e.tier === 2 || /rule|risk|signal|query|eligibility/.test(n)) return 'operator'
  return 'model'
}

export function mapEntities(entities: EntityListItem[]): G6NodeData[] {
  return entities.map(e => ({
    id: e.id,
    data: {
      label: e.name_cn || e.name,
      subLabel: `${e.relation_count}关系 · ${e.rule_count}规则`,
      nodeType: classifyNode(e),
      tier: e.tier,
      status: e.status,
      relationCount: e.relation_count,
      ruleCount: e.rule_count,
      attrCount: e.attr_count ?? 0,
      actionCount: e.action_count ?? 0,
    },
  }))
}

export function mapRelations(relations: RelationData[], nodeIds: Set<string>): G6EdgeData[] {
  return relations
    .filter(r => nodeIds.has(r.from_entity_id) && nodeIds.has(r.to_entity_id))
    .map(r => ({
      id: r.id,
      source: r.from_entity_id,
      target: r.to_entity_id,
      data: {
        label: r.name.replaceAll('_', ' '),
        cardinality: r.cardinality || '1:N',
      },
    }))
}
