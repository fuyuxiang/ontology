import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ruleApi } from '../api/rules'

// 后端返回的 snake_case 格式
interface RuleRaw {
  id: string
  name: string
  entity_id: string
  entity_name: string
  condition_expr: string
  action_desc: string
  status: string
  priority: string
  trigger_count: number
  last_triggered: string | null
}

// 前端模板使用的格式
export interface RuleMapped {
  id: string
  name: string
  entityId: string
  entityName: string
  condition: string
  action: string
  status: string
  priority: string
  triggerCount: number
  lastTriggered: string | null
}

function mapRule(r: RuleRaw): RuleMapped {
  return {
    id: r.id, name: r.name,
    entityId: r.entity_id, entityName: r.entity_name,
    condition: r.condition_expr, action: r.action_desc,
    status: r.status, priority: r.priority,
    triggerCount: r.trigger_count, lastTriggered: r.last_triggered,
  }
}

export const useRulesStore = defineStore('rules', () => {
  const rawRules = ref<RuleRaw[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const filter = ref<{ status: string; search: string }>({ status: 'all', search: '' })

  const rules = computed(() => rawRules.value.map(mapRule))

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

  async function fetchRules(query?: { entityId?: string; status?: string; priority?: string }) {
    loading.value = true
    error.value = null
    try {
      rawRules.value = await ruleApi.list(query as never) as unknown as RuleRaw[]
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

  return { rules, rawRules, loading, error, filter, filtered, stats, fetchRules, executeRule }
})
