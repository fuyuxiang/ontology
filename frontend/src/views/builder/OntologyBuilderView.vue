<template>
  <!-- 空状态欢迎页（自带 .ob-root.ob-empty-root） -->
  <EmptyWelcome
    v-if="!sessions.length && !activeSession"
    @open-new="openNewModal('ai')"
    @open-upload="openNewModal('upload')"
  >
    <template #modal>
      <NewOntologyModal
        v-if="newModalOpen"
        :default-method="defaultMethod"
        @update:open="newModalOpen = $event"
        @submit="onCreateSession"
      />
    </template>
  </EmptyWelcome>

  <!-- 最近构建表（自带 .ob-root） -->
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useBuilderStore } from '../../store/builder'
import type { BuildMethod, BuilderSession } from '../../types/builder'

import EmptyWelcome from './components/EmptyWelcome.vue'
import RecentBuildTable from './components/RecentBuildTable.vue'
import NewOntologyModal from './components/NewOntologyModal.vue'
import BuilderShell from './components/BuilderShell.vue'

const router = useRouter()
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
  scenarioId: string
  scenarioName: string
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
</script>
