import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ruleApi } from '../api/rules'
import type { BusinessRule, RuleStatus, Priority } from '../types'

export const useRulesStore = defineStore('rules', () => {
  const rules = ref<BusinessRule[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const filter = ref<{ status: RuleStatus | 'all'; search: string }>({ status: 'all', search: '' })

  const filtered = computed(() => {
    let list = rules.value
    if (filter.value.status !== 'all') {
      list = list.filter(r => r.status === filter.value.status)
    }
    if (filter.value.search) {
      const q = filter.value.search.toLowerCase()
      list = list.filter(r =>
        r.name.toLowerCase().includes(q) ||
        r.id.toLowerCase().includes(q) ||
        r.condition.toLowerCase().includes(q)
      )
    }
    return list
  })

  const stats = computed(() => ({
    total: rules.value.length,
    active: rules.value.filter(r => r.status === 'active').length,
    warning: rules.value.filter(r => r.status === 'warning').length,
    disabled: rules.value.filter(r => r.status === 'disabled').length,
  }))

  async function fetchRules(query?: { entityId?: string; status?: RuleStatus; priority?: Priority }) {
    loading.value = true
    error.value = null
    try {
      rules.value = await ruleApi.list(query)
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function executeRule(id: string) {
    try {
      return await ruleApi.execute(id)
    } catch (e: unknown) {
      error.value = (e as Error).message
      return null
    }
  }

  return { rules, loading, error, filter, filtered, stats, fetchRules, executeRule }
})
