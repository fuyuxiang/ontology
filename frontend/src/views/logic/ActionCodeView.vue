<template>
  <div class="code-server-page">
    <div class="code-server-page__header">
      <button class="btn-back" @click="goBack">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回动作列表
      </button>
      <span class="code-server-page__title">{{ actionName || '动作编辑' }}</span>
    </div>
    <div v-if="loading" class="code-server-page__loading">
      <p>正在准备工作区…</p>
    </div>
    <div v-else-if="error" class="code-server-page__error">
      <p>{{ error }}</p>
      <button class="btn-primary" @click="goBack">返回</button>
    </div>
    <iframe
      v-else
      :src="codeServerUrl"
      class="code-server-page__iframe"
      frameborder="0"
      allow="clipboard-read; clipboard-write"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { actionApi } from '../../api/actions'

const route = useRoute()
const router = useRouter()

const codeServerUrl = ref('')
const actionName = ref('')
const loading = ref(true)
const error = ref('')

function goBack() {
  if (route.query.from === 'ontology' && route.query.code) {
    router.push(`/ontology/list/${route.query.code}`)
  } else {
    router.push('/logic/actions')
  }
}

onMounted(async () => {
  const actionId = route.params.id as string
  if (!actionId) { error.value = '缺少动作ID'; loading.value = false; return }

  try {
    const action = await actionApi.detail(actionId)
    actionName.value = action.name

    const ws = await actionApi.openWorkspace(actionId)
    codeServerUrl.value = ws.url
  } catch (err: any) {
    error.value = err?.message || '打开工作区失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.code-server-page { display: flex; flex-direction: column; height: 100vh; background: #1e1e2e; }
.code-server-page__header { display: flex; align-items: center; gap: 16px; padding: 12px 20px; background: #181825; border-bottom: 1px solid #313244; }
.btn-back { display: flex; align-items: center; gap: 6px; padding: 6px 12px; border: 1px solid #45475a; border-radius: 6px; background: transparent; color: #cdd6f4; font-size: 13px; cursor: pointer; transition: background .15s; }
.btn-back:hover { background: #313244; }
.code-server-page__title { color: #cdd6f4; font-size: 14px; font-weight: 500; }
.code-server-page__iframe { flex: 1; width: 100%; border: none; }
.code-server-page__loading, .code-server-page__error { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #a6adc8; }
.btn-primary { padding: 8px 16px; border: none; border-radius: 6px; background: #89b4fa; color: #1e1e2e; font-weight: 500; cursor: pointer; margin-top: 12px; }
</style>
