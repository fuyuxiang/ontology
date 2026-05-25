import { get, post } from './client'
import type { ProbeRequest, QualityMetric, QualityKind } from '../types/quality'

const KINDS: QualityKind[] = ['row_count', 'freshness', 'null_ratio',
  'distinct_count', 'pk_uniqueness', 'schema_drift']

export function runProbe(kind: QualityKind, body: ProbeRequest) {
  if (!KINDS.includes(kind)) throw new Error(`unknown probe kind: ${kind}`)
  return post<QualityMetric>(`/probes/${kind}`, body)
}

export function listAssetProbes(
  assetId: string,
  params?: { kind?: QualityKind; column?: string; since?: string },
) {
  return get<QualityMetric[]>(`/probes/asset/${assetId}`, { params })
}
