<template>
  <div class="dash-wrap">
    <OntologyOperationsBoard
      :stats="stats"
      :entities="entities"
      :relations="relations"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import OntologyOperationsBoard from '../../components/dashboard/OntologyOperationsBoard.vue'
import { dashboardApi } from '../../api/dashboard'
import { entityApi } from '../../api/ontology'
import { relationApi } from '../../api/relations'
import type { DashboardStats } from '../../types'

const stats = ref<DashboardStats | null>(null)
const entities = ref<any[]>([])
const relations = ref<any[]>([])

onMounted(async () => {
  const [s, e, r] = await Promise.all([
    dashboardApi.stats().catch(() => null),
    entityApi.list().catch(() => []),
    relationApi.list().catch(() => []),
  ])
  stats.value = s as any
  entities.value = e
  relations.value = r
})
</script>

<style scoped>
.dash-wrap {
  width: 100%;
  height: 100%;
  overflow-y: auto;
}
</style>
