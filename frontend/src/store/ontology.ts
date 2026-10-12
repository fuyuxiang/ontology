import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useAuthStore } from './auth'
import { entityApi } from '../api/ontology'
import type { EntityListItem, OntologyEntity, GraphData, Tier } from '../types'

export const useOntologyStore = defineStore('ontology', () => {
  const entities = ref<EntityListItem[]>([])
  const currentEntity = ref<OntologyEntity | null>(null)
  const graphData = ref<GraphData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentOntologyId = ref<string | null>(null)
  let entitiesRequest = 0, detailRequest = 0, graphRequest = 0
  const auth = useAuthStore()
  watch(() => auth.user?.id, () => { ++entitiesRequest; ++detailRequest; ++graphRequest; entities.value = []; currentEntity.value = null; graphData.value = null; currentOntologyId.value = null; loading.value = false; error.value = null }, {flush:'sync'})

  const tier1 = computed(() => entities.value.filter(e => e.tier === 1))
  const tier2 = computed(() => entities.value.filter(e => e.tier === 2))
  const tier3 = computed(() => entities.value.filter(e => e.tier === 3))

  const grouped = computed(() => [
    { tier: 1 as Tier, label: 'Tier 1 核心对象', entities: tier1.value },
    { tier: 2 as Tier, label: 'Tier 2 领域对象', entities: tier2.value },
    { tier: 3 as Tier, label: 'Tier 3 场景对象', entities: tier3.value },
  ])

  async function fetchEntities(query?: { tier?: Tier; search?: string; ontology_id?: string }) {
    if (!auth.user) {
      const sessionToken = auth.token
      if (!sessionToken) return
      await auth.fetchUser()
      // A caller waiting for account A must not start a request as account B.
      if (!auth.user || !auth.token || auth.token !== sessionToken) return
    }
    const request = ++entitiesRequest
    loading.value = true
    error.value = null
    try {
      const params = { ...query }
      if (!params.ontology_id && currentOntologyId.value) {
        params.ontology_id = currentOntologyId.value
      }
      const items = await entityApi.list(params)
      if (request === entitiesRequest) entities.value = items
    } catch (e: unknown) {
      if (request === entitiesRequest) error.value = (e as Error).message
    } finally {
      if (request === entitiesRequest) loading.value = false
    }
  }

  async function switchOntology(id: string) {
    if (!auth.user) {
      const sessionToken = auth.token
      if (!sessionToken) return
      await auth.fetchUser()
      // A caller waiting for account A must not start a request as account B.
      if (!auth.user || !auth.token || auth.token !== sessionToken) return
    }
    ++detailRequest; ++graphRequest
    currentOntologyId.value = id
    entities.value = []; currentEntity.value = null; graphData.value = null
    await fetchEntities({ ontology_id: id })
  }

  async function fetchEntity(id: string) {
    if (!auth.user) {
      const sessionToken = auth.token
      if (!sessionToken) return
      await auth.fetchUser()
      // A caller waiting for account A must not start a request as account B.
      if (!auth.user || !auth.token || auth.token !== sessionToken) return
    }
    const request = ++detailRequest
    loading.value = true
    error.value = null
    try {
      const detail = await entityApi.detail(id)
      if (request === detailRequest) currentEntity.value = detail
    } catch (e: unknown) {
      if (request === detailRequest) error.value = (e as Error).message
    } finally {
      if (request === detailRequest) loading.value = false
    }
  }

  async function fetchGraph(entityId?: string) {
    if (!auth.user) {
      const sessionToken = auth.token
      if (!sessionToken) return
      await auth.fetchUser()
      // A caller waiting for account A must not start a request as account B.
      if (!auth.user || !auth.token || auth.token !== sessionToken) return
    }
    const request = ++graphRequest
    loading.value = true
    try {
      const graph = entityId
        ? await entityApi.graph(entityId)
        : await entityApi.graphAll()
      if (request === graphRequest) graphData.value = graph
    } catch (e: unknown) {
      if (request === graphRequest) error.value = (e as Error).message
    } finally {
      if (request === graphRequest) loading.value = false
    }
  }

  async function removeEntity(id: string, force = false) {
    await entityApi.remove(id, force)
    entities.value = entities.value.filter(e => e.id !== id)
  }

  return {
    entities, currentEntity, graphData, loading, error,
    tier1, tier2, tier3, grouped, currentOntologyId,
    fetchEntities, fetchEntity, fetchGraph, switchOntology, removeEntity,
  }
})
