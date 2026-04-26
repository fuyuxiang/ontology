import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { DataSource } from '../types/datasource'
import * as api from '../api/datasource'

export const useDataSourceStore = defineStore('datasource', () => {
  const items = ref<DataSource[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const stats = computed(() => {
    const total = items.value.length
    const active = items.value.filter(d => d.status === 'active').length
    const enabled = items.value.filter(d => d.enabled).length
    const stopped = items.value.filter(d => !d.enabled).length
    const errorCount = items.value.filter(d => d.status === 'error').length
    return { total, active, enabled, stopped, error: errorCount }
  })

  async function fetchList(params?: { type?: string; status?: string; q?: string }) {
    loading.value = true
    error.value = null
    try {
      items.value = await api.listDataSources(params)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  return { items, loading, error, stats, fetchList }
})
