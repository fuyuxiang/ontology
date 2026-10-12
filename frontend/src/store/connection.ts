import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import * as api from '../api/connection'
import type { Connection, ConnectionCreate, ConnectionUpdate } from '../types/connection'

export const useConnectionStore = defineStore('connection', () => {
  const items = ref<Connection[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  let listRequest = 0
  const auth = useAuthStore()
  let accountGeneration = 0
  watch(() => auth.user?.id, () => { ++accountGeneration; ++listRequest; items.value = []; loading.value = false; error.value = null;  }, {flush:'sync'})

  const stats = computed(() => {
    const total = items.value.length
    const active = items.value.filter(c => c.status === 'active').length
    const enabled = items.value.filter(c => c.enabled).length
    const stopped = items.value.filter(c => !c.enabled).length
    const errorCount = items.value.filter(c => c.status === 'error').length
    return { total, active, enabled, stopped, error: errorCount }
  })

  async function fetchList(params?: { type?: string; category?: string; status?: string; q?: string }) {
    if (!auth.user) {
      const sessionToken = auth.token
      if (!sessionToken) return
      await auth.fetchUser()
      // A caller waiting for account A must not start a request as account B.
      if (!auth.user || !auth.token || auth.token !== sessionToken) return
    }
    const request = ++listRequest
    loading.value = true
    error.value = null
    try {
      const rows = await api.listConnections(params)
      if (request === listRequest) items.value = rows
    } catch (e: any) {
      if (request === listRequest) error.value = e.response?.data?.detail || e.message || '数据源加载失败'
    } finally {
      if (request === listRequest) loading.value = false
    }
  }

  async function create(body: ConnectionCreate) {
    const account = accountGeneration
    const row = await api.createConnection(body)
    if (account !== accountGeneration) return row
    items.value.unshift(row)
    return row
  }

  async function update(id: string, body: ConnectionUpdate) {
    const account = accountGeneration
    const row = await api.updateConnection(id, body)
    if (account !== accountGeneration) return row
    const idx = items.value.findIndex(c => c.id === id)
    if (idx >= 0) items.value[idx] = row
    return row
  }

  async function remove(id: string, cascade = false) {
    const account = accountGeneration
    await api.deleteConnection(id, cascade)
    if (account !== accountGeneration) return
    items.value = items.value.filter(c => c.id !== id)
  }

  async function test(id: string) {
    return api.testConnection(id)
  }

  async function toggle(id: string) {
    const account = accountGeneration
    const row = await api.toggleConnection(id)
    if (account !== accountGeneration) return row
    const idx = items.value.findIndex(c => c.id === id)
    if (idx >= 0) items.value[idx] = row
    return row
  }

  return { items, loading, error, stats, fetchList, create, update, remove, test, toggle }
})
