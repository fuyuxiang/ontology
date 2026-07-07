<template>
  <div class="code-server-page">
    <div class="code-server-page__header">
      <button class="btn-back" @click="goBack">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回函数列表
      </button>
      <span class="code-server-page__title">{{ funcName || '代码编辑' }}</span>
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
import { functionApi } from '../../api/functions'

const route = useRoute()
const router = useRouter()

const codeServerUrl = ref('')
const funcName = ref('')
const loading = ref(true)
const error = ref('')

function goBack() {
  router.push('/logic/functions')
}

onMounted(async () => {
  const funcId = route.params.id as string
  if (!funcId) { error.value = '缺少函数ID'; loading.value = false; return }

  try {
    const func = await functionApi.detail(funcId)
    funcName.value = func.name

    const ws = await functionApi.openWorkspace(funcId)
    codeServerUrl.value = ws.url
  } catch (err: any) {
    error.value = err?.message || '打开工作区失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.code-server-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--neutral-50, #fafafa);
}

.code-server-page__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: var(--neutral-0, #fff);
  border-bottom: 1px solid var(--neutral-200, #e5e5e5);
  flex-shrink: 0;
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: 6px;
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #333);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-back:hover {
  background: var(--neutral-50, #fafafa);
}

.code-server-page__title {
  font-size: 14px;
  font-weight: 500;
  color: var(--neutral-800, #333);
}

.code-server-page__iframe {
  flex: 1;
  width: 100%;
  border: none;
}

.code-server-page__loading,
.code-server-page__error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--neutral-500, #888);
}
</style>
