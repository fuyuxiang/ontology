<template>
  <!-- 空状态欢迎页 -->
  <EmptyWelcome
    v-if="!sessions.length && !activeSession"
    @open-method="openNewModal"
  >
    <template #modal>
      <NewOntologyModal
        v-if="newModalOpen"
        :open="newModalOpen"
        :default-method="defaultMethod"
        @update:open="newModalOpen = $event"
        @submit="onCreateSession"
      />
    </template>
  </EmptyWelcome>

  <!-- 最近构建表 -->
  <RecentBuildTable
    v-else-if="!activeSession"
    :sessions="sessions"
    @new="openNewModal()"
    @resume="onResume"
    @view="onView"
    @delete="onDelete"
  >
    <template #modal>
      <NewOntologyModal
        v-if="newModalOpen"
        :open="newModalOpen"
        :default-method="defaultMethod"
        @update:open="newModalOpen = $event"
        @submit="onCreateSession"
      />
    </template>
  </RecentBuildTable>

  <!-- 构建流程外壳 -->
  <BuilderShell
    v-else
    :session="activeSession"
    @back="exitToList"
    @goto-studio="gotoStudio"
  />
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useBuilderStore } from '../../store/builder'
import type { BuildMethod, BuilderSession } from '../../types/builder'

import EmptyWelcome from './components/EmptyWelcome.vue'
import RecentBuildTable from './components/RecentBuildTable.vue'
import NewOntologyModal from './components/NewOntologyModal.vue'
import BuilderShell from './components/BuilderShell.vue'

const router = useRouter()
const route = useRoute()
const store = useBuilderStore()
const { sessions, activeSession } = storeToRefs(store)

const newModalOpen = ref(false)
const defaultMethod = ref<BuildMethod | undefined>(undefined)

function openNewModal(method?: BuildMethod) {
  defaultMethod.value = method
  newModalOpen.value = true
}

function onCreateSession(payload: {
  ontologyName: string
  buildMethod: BuildMethod
}) {
  store.createSession(payload)
  newModalOpen.value = false
}

function onResume(s: BuilderSession) {
  store.setActiveSession(s.sessionId)
}
function onView(s: BuilderSession) {
  if (s.status === 'published') router.push('/studio')
  else onResume(s)
}
function onDelete(s: BuilderSession) {
  store.deleteSession(s.sessionId)
}
function exitToList() {
  store.setActiveSession(null)
}
function gotoStudio() {
  router.push('/studio')
}

// /logic/* 回流：?session_id=&attach_to=&new_id=&kind=rule|action|function
function captureBuilderReturn() {
  const q = route.query
  const sid = (q.session_id || '') as string
  const attachTo = (q.attach_to || '') as string
  const newId = (q.new_id || '') as string
  const kind = (q.kind || '') as 'rule' | 'action' | 'function' | ''
  if (!sid || !attachTo || !newId || !kind) return
  store.setActiveSession(sid)
  const session = store.activeSession
  if (!session) return
  const objects = session.ontologyObjects.map(o => {
    if (o.id !== attachTo) return o
    if (kind === 'rule')      return { ...o, rules: [...new Set([...o.rules, newId])] }
    if (kind === 'action')    return { ...o, actions: [...new Set([...o.actions, newId])] }
    if (kind === 'function')  return { ...o, derivedProperties: [...new Set([...o.derivedProperties, newId])] }
    return o
  })
  store.patchActive({ ontologyObjects: objects })
  // 清掉 query
  router.replace({ path: route.path })
}

onMounted(captureBuilderReturn)
watch(() => route.fullPath, captureBuilderReturn)
</script>
