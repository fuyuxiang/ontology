import { defineStore } from 'pinia'
import { ref } from 'vue'
import { auditApi } from '../api/audit'
import type { AuditEntry, AuditQuery } from '../types'

export const useAuditStore = defineStore('audit', () => {
  const entries = ref<AuditEntry[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchEntries(query?: AuditQuery) {
    loading.value = true
    error.value = null
    try {
      const res = await auditApi.list(query)
      entries.value = res.items
      total.value = res.total
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  return { entries, total, loading, error, fetchEntries }
})
