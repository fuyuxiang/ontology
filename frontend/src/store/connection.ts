import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from '../api/connection'
import type { Connection, ConnectionCreate, ConnectionUpdate } from '../types/connection'

export const useConnectionStore = defineStore('connection', () => {
  const items = ref<Connection[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const stats = computed(() => {
    const total = items.value.length
    const active = items.value.filter(c => c.status === 'active').length
    const enabled = items.value.filter(c => c.enabled).length
    const stopped = items.value.filter(c => !c.enabled).length
    const errorCount = items.value.filter(c => c.status === 'error').length
    return { total, active, enabled, stopped, error: errorCount }
  })

  async function fetchList(params?: { type?: string; category?: string; status?: string; q?: string }) {
    loading.value = true
    error.value = null
    try {
      items.value = await api.listConnections(params)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function create(body: ConnectionCreate) {
    const row = await api.createConnection(body)
    items.value.unshift(row)
    return row
  }

  async function update(id: string, body: ConnectionUpdate) {
    const row = await api.updateConnection(id, body)
    const idx = items.value.findIndex(c => c.id === id)
    if (idx >= 0) items.value[idx] = row
    return row
  }

  async function remove(id: string, cascade = false) {
    await api.deleteConnection(id, cascade)
    items.value = items.value.filter(c => c.id !== id)
  }

  async function test(id: string) {
    return api.testConnection(id)
  }

  async function toggle(id: string) {
    const row = await api.toggleConnection(id)
    const idx = items.value.findIndex(c => c.id === id)
    if (idx >= 0) items.value[idx] = row
    return row
  }

  return { items, loading, error, stats, fetchList, create, update, remove, test, toggle }
})
