<template>
  <div class="step-mapping">
    <h2 class="step-mapping__title">数据资产映射</h2>

    <div v-if="loading" class="step-mapping__loading">
      <div class="step-mapping__spinner"></div>
      <p>{{ progressMessage }}</p>
    </div>

    <div v-else-if="errorMessage" class="step-mapping__error">
      <p>{{ errorMessage }}</p>
      <button class="step-mapping__btn" @click="startMapping">重试</button>
    </div>

    <div v-else-if="mappedOntology" class="step-mapping__result">
      <p class="step-mapping__sub">
        共映射 {{ mappedOntology.entities.length }} 个实体、{{ mappedOntology.relations.length }} 个关系
      </p>

      <div class="step-mapping__section">
        <h3>实体映射</h3>
        <table class="step-mapping__table">
          <thead>
            <tr>
              <th>实体名称</th>
              <th>匹配表</th>
              <th>置信度</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="e in mappedOntology.entities"
              :key="e.name"
              :class="{ 'step-mapping__row--warning': !e.table, 'step-mapping__row--low': e.confidence < 0.8 && e.table }"
            >
              <td>{{ e.displayName || e.name }}</td>
              <td>
                <select v-model="e.table" class="step-mapping__select">
                  <option :value="null">未匹配</option>
                  <option v-for="t in candidateTables" :key="t" :value="t">{{ t }}</option>
                </select>
              </td>
              <td>
                <span class="step-mapping__confidence" :class="confidenceClass(e.confidence)">
                  {{ e.table ? Math.round((e.confidence || 0) * 100) + '%' : '-' }}
                </span>
              </td>
              <td>
                <button class="step-mapping__btn-sm" @click="toggleExpand(e.name)">
                  {{ expanded[e.name] ? '收起' : '展开' }}
                </button>
              </td>
            </tr>
            <template v-for="e in mappedOntology.entities" :key="'detail-' + e.name">
              <tr v-if="expanded[e.name]" class="step-mapping__detail-row">
                <td colspan="4">
                  <table class="step-mapping__sub-table">
                    <thead>
                      <tr><th>属性</th><th>匹配字段</th><th>字段类型</th><th>置信度</th></tr>
                    </thead>
                    <tbody>
                      <tr v-for="p in e.properties" :key="p.name">
                        <td>{{ p.displayName || p.name }}</td>
                        <td>
                          <select v-model="p.field" class="step-mapping__select step-mapping__select--sm">
                            <option :value="null">未匹配</option>
                            <option v-for="f in getFieldsForTable(e.table)" :key="f.field_name" :value="f.field_name">
                              {{ f.field_name }} ({{ f.field_desc || '' }})
                            </option>
                          </select>
                        </td>
                        <td>{{ p.fieldType || '-' }}</td>
                        <td>
                          <span class="step-mapping__confidence" :class="confidenceClass(p.confidence)">
                            {{ p.field ? Math.round((p.confidence || 0) * 100) + '%' : '-' }}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="step-mapping__section" v-if="mappedOntology.relations.length">
        <h3>关系映射</h3>
        <table class="step-mapping__table">
          <thead>
            <tr><th>关系</th><th>源表.字段</th><th>目标表.字段</th><th>置信度</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in mappedOntology.relations" :key="r.name" :class="{ 'step-mapping__row--low': r.confidence < 0.8 }">
              <td>{{ r.displayName || r.name }} ({{ r.source }}→{{ r.target }})</td>
              <td>{{ r.sourceTable ? `${r.sourceTable}.${r.sourceField}` : '-' }}</td>
              <td>{{ r.targetTable ? `${r.targetTable}.${r.targetField}` : '-' }}</td>
              <td>
                <span class="step-mapping__confidence" :class="confidenceClass(r.confidence)">
                  {{ Math.round((r.confidence || 0) * 100) }}%
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="step-mapping__actions">
        <button class="step-mapping__btn step-mapping__btn--secondary" @click="startMapping">重新匹配</button>
        <button class="step-mapping__btn" :disabled="!allEntitiesMapped" @click="onConfirm">确认并继续</button>
      </div>
      <p v-if="!allEntitiesMapped" class="step-mapping__hint">所有实体必须完成映射后才能继续</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'

const props = defineProps<{
  sessionId: string
  ontology: any
}>()

const emit = defineEmits<{
  next: [ontology: any]
}>()

const loading = ref(false)
const progressMessage = ref('')
const errorMessage = ref('')
const mappedOntology = ref<any>(null)
const candidateTables = ref<string[]>([])
const tableFields = reactive<Record<string, any[]>>({})
const expanded = reactive<Record<string, boolean>>({})

const allEntitiesMapped = computed(() => {
  if (!mappedOntology.value) return false
  return mappedOntology.value.entities.every((e: any) => e.table != null)
})

function confidenceClass(c: number | undefined) {
  if (!c) return 'step-mapping__confidence--none'
  if (c >= 0.8) return 'step-mapping__confidence--high'
  return 'step-mapping__confidence--low'
}

function toggleExpand(name: string) {
  expanded[name] = !expanded[name]
}

function getFieldsForTable(tableName: string | null): any[] {
  if (!tableName) return []
  return tableFields[tableName] || []
}

async function fetchTableFields(tableNames: string[]) {
  for (const tn of tableNames) {
    if (tableFields[tn]) continue
    try {
      const resp = await fetch(`/api/v1/ai-builder/tables/${tn}/schema`)
      if (resp.ok) {
        tableFields[tn] = await resp.json()
      }
    } catch { /* skip */ }
  }
}

async function startMapping() {
  loading.value = true
  errorMessage.value = ''
  progressMessage.value = '正在筛选候选表...'

  try {
    const resp = await fetch('/api/v1/doc-builder/mapping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: props.sessionId, ontology: props.ontology }),
    })

    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6)
        if (raw === '[DONE]') break
        try {
          const evt = JSON.parse(raw)
          if (evt.event === 'progress') {
            progressMessage.value = evt.message
          } else if (evt.event === 'error') {
            errorMessage.value = evt.message
            loading.value = false
            return
          } else if (evt.event === 'result') {
            mappedOntology.value = evt.data
            candidateTables.value = evt.candidate_tables || []
            await fetchTableFields(candidateTables.value)
          }
        } catch { /* skip non-json */ }
      }
    }
  } catch (e: any) {
    errorMessage.value = `请求失败: ${e.message}`
  }

  loading.value = false
}

function onConfirm() {
  emit('next', mappedOntology.value)
}

onMounted(() => {
  startMapping()
})
</script>

<style scoped>
.step-mapping { padding: 24px; max-width: 1000px; margin: 0 auto; }
.step-mapping__title { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
.step-mapping__sub { color: #666; margin-bottom: 16px; }
.step-mapping__loading { text-align: center; padding: 60px 0; }
.step-mapping__spinner { width: 32px; height: 32px; border: 3px solid #e0e0e0; border-top-color: #4a6fa5; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 12px; }
@keyframes spin { to { transform: rotate(360deg); } }
.step-mapping__error { text-align: center; padding: 40px 0; color: #d32f2f; }
.step-mapping__section { margin-bottom: 24px; }
.step-mapping__section h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.step-mapping__table { width: 100%; border-collapse: collapse; font-size: 13px; }
.step-mapping__table th, .step-mapping__table td { padding: 8px 12px; border: 1px solid #e0e0e0; text-align: left; }
.step-mapping__table th { background: #f5f5f5; font-weight: 600; }
.step-mapping__row--warning { background: #fff3e0; }
.step-mapping__row--low { background: #fffde7; }
.step-mapping__sub-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.step-mapping__sub-table th, .step-mapping__sub-table td { padding: 4px 8px; border: 1px solid #eee; }
.step-mapping__sub-table th { background: #fafafa; }
.step-mapping__detail-row td { padding: 0 !important; }
.step-mapping__select { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; max-width: 200px; }
.step-mapping__select--sm { max-width: 180px; }
.step-mapping__confidence--high { color: #2e7d32; font-weight: 600; }
.step-mapping__confidence--low { color: #f57c00; font-weight: 600; }
.step-mapping__confidence--none { color: #999; }
.step-mapping__actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px; }
.step-mapping__btn { padding: 8px 20px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; }
.step-mapping__btn:disabled { background: #ccc; cursor: not-allowed; }
.step-mapping__btn--secondary { background: #fff; color: #4a6fa5; border: 1px solid #4a6fa5; }
.step-mapping__btn-sm { padding: 2px 8px; font-size: 11px; background: #f0f0f0; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; }
.step-mapping__hint { color: #d32f2f; font-size: 12px; text-align: right; margin-top: 8px; }
</style>
