<template>
  <div class="dash-dark">
    <G6Canvas :entities="entities" :relations="relations" :stats="stats" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import G6Canvas from '../../components/dashboard/g6/G6Canvas.vue'
import { dashboardApi } from '../../api/dashboard'
import type { DashboardStatsEx } from '../../api/dashboard'
import { entityApi } from '../../api/ontology'
import { relationApi } from '../../api/relations'
import type { EntityListItem } from '../../types'
import type { RelationData } from '../../api/relations'

const stats = ref<DashboardStatsEx | null>(null)
const entities = ref<EntityListItem[]>([])
const relations = ref<RelationData[]>([])

onMounted(async () => {
  const [s, e, r] = await Promise.all([
    dashboardApi.stats().catch(() => null),
    entityApi.list().catch(() => []),
    relationApi.list().catch(() => []),
  ])
  stats.value = s as any
  entities.value = e as EntityListItem[]
  relations.value = r as RelationData[]
})
</script>

<style scoped>
.dash-dark {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0F172A;
}
</style>
