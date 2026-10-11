<template>
  <div class="code-server-page">
    <div class="code-server-page__header">
      <button class="btn-back" @click="goBack">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M10 12L6 8l4-4"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        返回动作列表
      </button>
      <span class="code-server-page__title">{{ actionName || '动作编辑' }}</span>
    </div>
    <div v-if="loading" class="code-server-page__loading" role="status">
      <p>正在准备工作区…</p>
    </div>
    <div v-else-if="error" class="code-server-page__error" role="alert">
      <p>{{ error }}</p>
      <button class="btn-primary" @click="loadWorkspace">重试</button>
      <button class="btn-back" @click="goBack">返回列表</button>
    </div>
    <iframe
      v-else
      :src="codeServerUrl"
      class="code-server-page__iframe"
      :title="`${actionName || '动作'}代码工作区`"
      frameborder="0"
      allow="clipboard-read; clipboard-write"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { actionApi } from '../../api/actions'
import { skillError } from '../../api/skills'
import { buildCodeServerUrl } from '../../utils/codeServer'

const route = useRoute()
const router = useRouter()

const codeServerUrl = ref('')
const actionName = ref('')
const loading = ref(true)
const error = ref('')
let requestGeneration = 0

function goBack() {
  if (route.query.from === 'ontology' && route.query.code) {
    router.push(`/ontology/list/${route.query.code}`)
  } else {
    router.push('/logic/actions')
  }
}

async function loadWorkspace() {
  const generation = ++requestGeneration
  const id = String(route.params.id || '')
  loading.value = true
  error.value = ''
  codeServerUrl.value = ''
  actionName.value = ''
  if (!id) {
    error.value = '缺少动作 ID'
    loading.value = false
    return
  }
  try {
    const item = await actionApi.detail(id)
    if (generation !== requestGeneration) return
    actionName.value = item.name
    const workspace = await actionApi.openWorkspace(id)
    if (generation === requestGeneration) codeServerUrl.value = buildCodeServerUrl(workspace)
  } catch (e) {
    if (generation === requestGeneration) error.value = skillError(e, '打开工作区失败')
  } finally {
    if (generation === requestGeneration) loading.value = false
  }
}
watch(() => route.params.id, loadWorkspace, { immediate: true })
onBeforeUnmount(() => {
  requestGeneration++
})
</script>

<style scoped>
.code-server-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 480px;
  min-width: 0;
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.code-server-page__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: var(--neutral-0);
  border-bottom: 1px solid var(--neutral-200);
  flex-shrink: 0;
}
.btn-back {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--neutral-200);
  border-radius: 6px;
  background: var(--neutral-0);
  color: var(--neutral-700);
  font-size: 13px;
  cursor: pointer;
}
.btn-back:hover {
  background: var(--neutral-50);
}
.code-server-page__title {
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 14px;
  font-weight: 500;
  color: var(--neutral-800);
}
.code-server-page__iframe {
  flex: 1;
  min-height: 360px;
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
  padding: 24px;
  color: var(--neutral-600);
  overflow-wrap: anywhere;
  text-align: center;
}
.btn-primary {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: var(--semantic-600);
  color: var(--neutral-0);
  cursor: pointer;
}
</style>
