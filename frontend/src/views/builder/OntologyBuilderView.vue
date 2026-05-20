<template>
  <div class="ob-root">
    <!-- 空状态欢迎页 -->
    <EmptyWelcome
      v-if="!sessions.length && !showRecent"
      @open-new="openNewModal('ai')"
      @open-upload="openNewModal('upload')"
    />

    <!-- 最近构建表 -->
    <RecentBuildTable
      v-else-if="!activeSession"
      :sessions="sessions"
      @new="openNewModal()"
      @resume="onResume"
      @view="onView"
      @delete="onDelete"
    />

    <!-- 构建流程外壳 -->
    <BuilderShell
      v-else
      :session="activeSession"
      @back="exitToList"
      @goto-studio="gotoStudio"
    />

    <!-- 新建本体弹窗 -->
    <NewOntologyModal
      v-model:open="newModalOpen"
      :default-method="defaultMethod"
      @submit="onCreateSession"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
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

const showRecent = computed(() => sessions.value.length > 0)
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
  if (s.status === 'published') {
    router.push('/studio')
  } else {
    onResume(s)
  }
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

<style scoped>
.ob-root {
  width: 100%;
  min-height: calc(100vh - 64px);
  background: #f8fafc;
  margin: -24px -32px;
  padding: 0;
}
</style>
