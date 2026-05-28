import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from '../api/asset'
import type { AssetFilters } from '../api/asset'
import type {
  Asset, AssetCreate, AssetUpdate, AssetWithUsage,
  DocumentSourceType,
} from '../types/asset'

export const useAssetStore = defineStore('asset', () => {
  const items = ref<Asset[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const usageCache = ref<Record<string, AssetWithUsage>>({})

  const stats = computed(() => {
    const total = items.value.length
    const tables = items.value.filter(a => a.kind === 'table').length
    const views = items.value.filter(a => a.kind === 'sql_view').length
    const documents = items.value.filter(a => a.kind === 'document').length
    const structured = tables + views
    const unstructured = documents
    const docByType: Record<DocumentSourceType, number> = {
      file: 0, oss: 0, directory: 0, api: 0, mq: 0,
    }
    for (const a of items.value) {
      if (a.kind === 'document' && a.document_source_type) {
        docByType[a.document_source_type] = (docByType[a.document_source_type] || 0) + 1
      }
    }
    return { total, tables, views, documents, structured, unstructured, docByType }
  })

  async function fetchList(params?: AssetFilters) {
    loading.value = true
    error.value = null
    try {
      // 后端的 status 默认是 'active'；明确传 undefined 让后端用默认
      items.value = await api.listAssets(params)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function refreshOne(id: string) {
    const row = await api.getAsset(id)
    const idx = items.value.findIndex(a => a.id === id)
    if (idx >= 0) items.value[idx] = row
    else items.value.unshift(row)
    return row
  }

  async function create(body: AssetCreate) {
    const row = await api.createAsset(body)
    items.value.unshift(row)
    return row
  }

  async function update(id: string, body: AssetUpdate) {
    const row = await api.updateAsset(id, body)
    const idx = items.value.findIndex(a => a.id === id)
    if (idx >= 0) items.value[idx] = row
    return row
  }

  async function remove(id: string) {
    await api.deleteAsset(id)
    items.value = items.value.filter(a => a.id !== id)
    delete usageCache.value[id]
  }

  async function fetchUsage(id: string) {
    const u = await api.getAssetUsage(id)
    usageCache.value[id] = u
    return u
  }

  async function syncSchema(id: string) {
    const r = await api.syncAssetSchema(id)
    await refreshOne(id)
    return r
  }

  async function profile(id: string) {
    const r = await api.profileAsset(id)
    await refreshOne(id)
    return r
  }

  async function preview(id: string, limit = 20) {
    return api.previewAsset(id, limit)
  }

  return {
    items, loading, error, stats, usageCache,
    fetchList, refreshOne, create, update, remove,
    fetchUsage, syncSchema, profile, preview,
  }
})
