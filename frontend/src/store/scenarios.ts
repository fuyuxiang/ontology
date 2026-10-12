import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useAuthStore } from './auth'
import { scenarioApi, type Scenario } from '../api/scenarios'

export const useScenarioStore = defineStore('scenarios', () => {
  const scenarios = ref<Scenario[]>([])
  const loaded = ref(false)
  const loading = ref(false)
  const auth = useAuthStore()
  let generation = 0
  watch(() => auth.user?.id, () => { ++generation; scenarios.value = []; loaded.value = false; loading.value = false }, {flush:'sync'})

  async function fetchScenarios(force = false) {
    if (!auth.user) {
      const sessionToken = auth.token
      if (!sessionToken) return
      await auth.fetchUser()
      // A caller waiting for account A must not start a request as account B.
      if (!auth.user || !auth.token || auth.token !== sessionToken) return
    }
    if (loaded.value && !force) return
    const request = ++generation
    loading.value = true
    try {
      const rows = await scenarioApi.list()
      if (request === generation) { scenarios.value = rows; loaded.value = true }
    } finally {
      if (request === generation) loading.value = false
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
