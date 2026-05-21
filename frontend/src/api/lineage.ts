import { get } from './client'

export interface LineageRow {
  key: string
  source: string  // 多行文本以 \n 分隔
  etl: string
  ontologyId: string
  objectName: string
  ontologyLabel: string
  tier: number
  app: string
}

export interface LineageCrossEdge {
  id: string
  source: string  // ontologyId
  target: string
}

export interface LineageWorkshopGraph {
  rows: LineageRow[]
  crossEdges: LineageCrossEdge[]
}

export interface FieldMapping {
  from: string
  to: string
  apiName: string
  type: string
}

export interface FieldLineageGroup {
  source: string
  fields: FieldMapping[]
}

export interface FieldLineageResponse {
  ontologyId: string
  objectName: string
  ontologyLabel: string
  groups: FieldLineageGroup[]
}

export const lineageApi = {
  workshop() {
    return get<LineageWorkshopGraph>('/lineage/workshop')
  },
  objectFields(ontologyId: string) {
    return get<FieldLineageResponse>(`/lineage/workshop/objects/${ontologyId}`)
  },
}
