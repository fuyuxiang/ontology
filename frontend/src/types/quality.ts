// 数据质量指标

export type QualityKind =
  | 'row_count' | 'freshness' | 'null_ratio' | 'distinct_count'
  | 'pk_uniqueness' | 'schema_drift'

export type QualitySeverity = 'ok' | 'warning' | 'error'

export interface QualityMetric {
  id: string
  asset_id: string
  kind: QualityKind
  column_name: string | null
  value_numeric: number | null
  value_text: string | null
  threshold: number | null
  severity: QualitySeverity
  measured_at: string
}

export interface ProbeRequest {
  asset_id: string
  column?: string | null
  threshold?: number | null
}
