<template>
  <div class="builder-page">
    <Step1Build v-if="session" :session="session" @next="onNext" />
    <div v-else class="builder-page__loading">正在初始化…</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useBuilderStore } from '../../store/builder'
import Step1Build from './components/Step1Build.vue'

const router = useRouter()
const store = useBuilderStore()
const { sessions, activeSession } = storeToRefs(store)

const session = computed(() => {
  if (activeSession.value && activeSession.value.buildMethod === 'chat') return activeSession.value
  return sessions.value.find(s => s.buildMethod === 'chat' && s.status === 'drafting') || null
})

function onNext() {
  router.push('/studio')
}

onMounted(() => {
  if (!session.value) {
    store.createSession({
      ontologyName: `AI构建-${Date.now().toString(36).slice(-4)}`,
      buildMethod: 'chat',
    })
  } else {
    store.setActiveSession(session.value.sessionId)
  }
})
</script>

<style scoped>
.builder-page { height: 100%; display: flex; flex-direction: column; }
.builder-page__loading { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--neutral-500); }
</style>
