import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from '../api/dataAudit'
import type { ExecutionLog, ExecutionStats } from '../types/execution'

export const useExecutionStore = defineStore('execution', () => {
  const items = ref<ExecutionLog[]>([])
  const stats = ref<ExecutionStats | null>(null)
  const loading = ref(false)

  async function fetchList(params?: api.AuditFilters) {
    loading.value = true
    try {
      items.value = await api.listExecutionLogs(params)
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    stats.value = await api.getExecutionStats()
  }

  async function getOne(id: string) {
    return api.getExecutionLog(id)
  }

  return { items, stats, loading, fetchList, fetchStats, getOne }
})
