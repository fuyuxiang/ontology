// ObjectBinding 强类型映射类型

export type BindingRole = 'primary' | 'enrichment' | 'document_evidence'

export interface FieldMapping {
  attribute_id: string
  source_column: string
  transform?: string | null
}

export interface ObjectBinding {
  id: string
  object_type_id: string
  asset_id: string
  role: BindingRole
  field_mappings: FieldMapping[]
  id_column: string | null
  filter_expr: string | null
  status: 'active' | 'needs_review' | 'deprecated'
  review_reason: string | null
  created_at: string
  updated_at: string
}

export interface BindingCreate {
  object_type_id: string
  asset_id: string
  role?: BindingRole
  field_mappings?: FieldMapping[]
  id_column?: string | null
  filter_expr?: string | null
}

export interface BindingUpdate {
  field_mappings?: FieldMapping[]
  id_column?: string | null
  filter_expr?: string | null
  status?: ObjectBinding['status']
  review_reason?: string | null
}

export interface BindingTestResolveResult {
  columns: string[]
  rows: unknown[][]
  field_mappings: FieldMapping[]
}
