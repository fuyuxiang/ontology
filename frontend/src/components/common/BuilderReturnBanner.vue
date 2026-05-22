<template>
  <div v-if="active" class="brb">
    <span class="brb-icon">↩</span>
    <div class="brb-text">
      正在为构建器
      <strong v-if="objectLabel">「{{ objectLabel }}」</strong>
      创建{{ kindLabel }}，保存后将返回构建器并自动挂载到该对象。
    </div>
    <button class="brb-cancel" @click="cancel">取消返回</button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

defineProps<{ kindLabel: string }>()
const route = useRoute()
const router = useRouter()

const objectLabel = ref('')

const active = computed(() => route.query.from === 'builder')

onMounted(async () => {
  const oid = (route.query.object_id || '') as string
  if (!oid) return
  // 优先从 builder store 取（已加载）
  try {
    const { useBuilderStore } = await import('../../store/builder')
    const store = useBuilderStore()
    const sid = (route.query.session_id || '') as string
    const sess = store.sessions.find(s => s.sessionId === sid)
    const obj = sess?.ontologyObjects.find(o => o.id === oid)
    if (obj) {
      objectLabel.value = obj.displayName || obj.name
      return
    }
  } catch { /* fall through */ }
  // 兜底：直接显示 object_id
  objectLabel.value = oid
})

function cancel() {
  router.replace({ path: route.path })
}
</script>

<style scoped>
.brb {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; margin: 12px 24px 0;
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.3);
  border-radius: 10px;
  font-size: 13px; color: #4338ca;
}
.brb-icon { font-size: 16px; }
.brb-text { flex: 1; }
.brb-text strong { color: #1e1b4b; }
.brb-cancel {
  padding: 4px 12px; border-radius: 6px;
  background: #fff; border: 1px solid #e0e7ff;
  color: #4f46e5; font-size: 11px; cursor: pointer;
}
.brb-cancel:hover { border-color: #4f46e5; background: #eef2ff; }
</style>
