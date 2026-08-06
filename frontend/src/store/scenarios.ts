import { defineStore } from 'pinia'
import { ref } from 'vue'
import { scenarioApi, type Scenario } from '../api/scenarios'

export const useScenarioStore = defineStore('scenarios', () => {
  const scenarios = ref<Scenario[]>([])
  const loaded = ref(false)
  const loading = ref(false)

  async function fetchScenarios(force = false) {
    if (loaded.value && !force) return
    loading.value = true
    try {
      scenarios.value = await scenarioApi.list()
      loaded.value = true
    } finally {
      loading.value = false
    }
  }

  function byCode(code: string): Scenario | undefined {
    return scenarios.value.find(s => s.code === code)
  }

  /** 强制重新拉取，用于逻辑/动作/对象增删后刷新本体统计计数 */
  async function refreshScenarios() {
    return fetchScenarios(true)
  }

  return { scenarios, loaded, loading, fetchScenarios, refreshScenarios, byCode }
})
