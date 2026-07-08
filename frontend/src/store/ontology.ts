import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { entityApi } from '../api/ontology'
import type { EntityListItem, OntologyEntity, GraphData, Tier } from '../types'

export const useOntologyStore = defineStore('ontology', () => {
  const entities = ref<EntityListItem[]>([])
  const currentEntity = ref<OntologyEntity | null>(null)
  const graphData = ref<GraphData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentOntologyId = ref<string | null>(null)

  const tier1 = computed(() => entities.value.filter(e => e.tier === 1))
  const tier2 = computed(() => entities.value.filter(e => e.tier === 2))
  const tier3 = computed(() => entities.value.filter(e => e.tier === 3))

  const grouped = computed(() => [
    { tier: 1 as Tier, label: 'Tier 1 核心对象', entities: tier1.value },
    { tier: 2 as Tier, label: 'Tier 2 领域对象', entities: tier2.value },
    { tier: 3 as Tier, label: 'Tier 3 场景对象', entities: tier3.value },
  ])

  async function fetchEntities(query?: { tier?: Tier; search?: string; ontology_id?: string }) {
    loading.value = true
    error.value = null
    try {
      const params = { ...query }
      if (!params.ontology_id && currentOntologyId.value) {
        params.ontology_id = currentOntologyId.value
      }
      entities.value = await entityApi.list(params)
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function switchOntology(id: string) {
    currentOntologyId.value = id
    entities.value = []
    await fetchEntities({ ontology_id: id })
  }

  async function fetchEntity(id: string) {
    loading.value = true
    error.value = null
    try {
      currentEntity.value = await entityApi.detail(id)
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function fetchGraph(entityId?: string) {
    loading.value = true
    try {
      graphData.value = entityId
        ? await entityApi.graph(entityId)
        : await entityApi.graphAll()
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function removeEntity(id: string) {
    await entityApi.remove(id)
    entities.value = entities.value.filter(e => e.id !== id)
  }

  return {
    entities, currentEntity, graphData, loading, error,
    tier1, tier2, tier3, grouped, currentOntologyId,
    fetchEntities, fetchEntity, fetchGraph, switchOntology, removeEntity,
  }
})
