import { get, post, put, del } from './client'
import type {
  ApiDocCreate, Asset, AssetCreate, AssetUpdate, AssetWithUsage,
  DirectoryDocCreate, DocumentSourceType, MqDocCreate, OssDocCreate,
  PreviewResult, SchemaSyncResult,
} from '../types/asset'
import type { QualityMetric } from '../types/quality'

export interface AssetFilters {
  kind?: string
  kinds?: string[]
  connection_id?: string
  domain?: string
  document_source_type?: DocumentSourceType
  status?: string
  q?: string
}

export function listAssets(params?: AssetFilters) {
  return get<Asset[]>('/assets', { params })
}

export function getAsset(id: string) {
  return get<Asset>(`/assets/${id}`)
}

export function getAssetUsage(id: string) {
  return get<AssetWithUsage>(`/assets/${id}/usage`)
}

export function createAsset(data: AssetCreate) {
  return post<Asset>('/assets', data)
}

export function updateAsset(id: string, data: AssetUpdate) {
  return put<Asset>(`/assets/${id}`, data)
}

export function deleteAsset(id: string) {
  return del<void>(`/assets/${id}`)
}

export function deprecateAsset(id: string, reason?: string) {
  return post<Asset>(`/assets/${id}/deprecate`, undefined, { params: reason ? { reason } : {} })
}

export function syncAssetSchema(id: string) {
  return post<SchemaSyncResult>(`/assets/${id}/sync-schema`)
}

export function profileAsset(id: string) {
  return post<{ row_count: number; null_ratio: Record<string, number>; sampled_at: string }>(
    `/assets/${id}/profile`,
  )
}

export function previewAsset(id: string, limit = 20) {
  return post<PreviewResult>(`/assets/${id}/preview`, undefined, { params: { limit } })
}

export function getAssetQuality(id: string, params?: { kind?: string; since?: string }) {
  return get<QualityMetric[]>(`/assets/${id}/quality`, { params })
}

// ── 5 种 document 接入 ─────────────────────────────────────

export function uploadDocumentAsset(file: File, opts?: {
  name?: string; description?: string; domain?: string; tags?: string
}) {
  const fd = new FormData()
  fd.append('file', file)
  if (opts?.name !== undefined) fd.append('name', opts.name)
  if (opts?.description) fd.append('description', opts.description)
  if (opts?.domain) fd.append('domain', opts.domain)
  if (opts?.tags) fd.append('tags', opts.tags)
  return post<Asset>('/assets/document/upload', fd)
}

export function createOssDocAsset(data: OssDocCreate) {
  return post<Asset>('/assets/document/oss', data)
}

export function createDirectoryDocAsset(data: DirectoryDocCreate) {
  return post<Asset>('/assets/document/directory', data)
}

export function createApiDocAsset(data: ApiDocCreate) {
  return post<Asset>('/assets/document/api', data)
}

export function createMqDocAsset(data: MqDocCreate) {
  return post<Asset>('/assets/document/mq', data)
}
