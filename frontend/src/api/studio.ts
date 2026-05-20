import { get } from './client'

export interface StudioProperty {
  apiName: string
  displayName: string
  dataType: string
  physicalName: string
  required: boolean
  isDerived: boolean
  description: string
  valueConstraint: unknown
  enum: unknown
  sourceColumn: string | null
  sourceTable: string | null
  dataStatus: string
}

export interface StudioObjectType {
  apiName: string
  displayName: string
  primaryKey: string
  titleProperty: string
  tier: 1 | 2 | 3
  scenarioCode: string
  status: string
  visibility: string
  iriPattern: string
  aboxScale: number
  dataSource: string
  description: string
  remarks: string[]
  properties: StudioProperty[]
  ruleCount: number
  actionCount: number
  functionCount: number
}

export interface StudioLinkType {
  apiName: string
  displayName: string
  source: string
  target: string
  cardinality: string
  relType: string
  acyclic: boolean
  description: string
}

export interface StudioTBox {
  kind: 'tbox'
  version: string
  generatedAt: string
  source: string
  meta: {
    objectTypeCount: number
    propertyCount: number
    linkTypeCount: number
    scenarios: string[]
    tierBreakdown: Record<string, string[]>
  }
  objectTypes: StudioObjectType[]
  linkTypes: StudioLinkType[]
}

export interface StudioHydration {
  objectTypeApiName: string
  level: 'full' | 'partial' | 'mapping' | 'none'
  instanceCount: number
  propertyCompleteness: {
    total: number
    mapped: number
    populated: number
    coverage: number
  }
  backingSource: string
}

export interface StudioABox {
  kind: 'abox'
  version: string
  generatedAt: string
  meta: {
    individualCount: number
    linkCount: number
    scenarios: string[]
  }
  individuals: unknown[]
  hydration: StudioHydration[]
}

export interface StudioRule {
  rule_id: string
  display_name: string
  category: string
  priority: string
  condition: unknown
  action: { reason: string; type: string }
  applicable_objects: string[]
  scenarioCode: string
  status: string
  trigger_count: number
}

export interface StudioRBox {
  kind: 'rbox'
  version: string
  meta: {
    ruleFamilyCount: number
    ruleCount: number
    scenarios: string[]
  }
  rules: StudioRule[]
  ruleFamilies: { familyId: string; displayName: string; ruleCount: number }[]
  constraints: unknown[]
}

export interface StudioStats {
  generatedAt: string
  tbox: {
    objectTypeCount: number
    propertyCount: number
    linkTypeCount: number
    tierBreakdown: Record<string, string[]>
    scenarioBreakdown: Record<string, number>
  }
  capability: {
    actionCount: number
    functionCount: number
    skillCount: number
    toolCount: number
    modelCount: number
  }
  rbox: {
    ruleFamilyCount: number
    ruleCount: number
    byFamily: Record<string, number>
  }
  abox: {
    individualCount: number
    linkCount: number
  }
}

export const studioApi = {
  tbox: () => get<StudioTBox>('/studio/tbox'),
  abox: () => get<StudioABox>('/studio/abox'),
  rbox: () => get<StudioRBox>('/studio/rbox'),
  capability: () => get<unknown>('/studio/capability'),
  stats: () => get<StudioStats>('/studio/stats'),
}
