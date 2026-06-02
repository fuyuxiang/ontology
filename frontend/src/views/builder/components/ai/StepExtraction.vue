<template>
  <div class="step-extract">
    <h2 class="step-extract__title">AI 正在提取本体</h2>
    <p class="step-extract__sub">基于 {{ tableNames.length }} 张表 + {{ documentKeys.length }} 篇文档，大模型正在分析...</p>

    <!-- Progress -->
    <div class="step-extract__progress">
      <div v-for="msg in progressMessages" :key="msg" class="step-extract__progress-item">✓ {{ msg }}</div>
      <div v-if="streaming" class="step-extract__progress-item step-extract__progress-item--active">⟳ 正在生成中...</div>
    </div>

    <!-- Result -->
    <div v-if="result" class="step-extract__result">
      <div class="step-extract__stats">
        <div class="step-extract__stat"><span class="step-extract__stat-num">{{ result.entities.length }}</span> 实体</div>
        <div class="step-extract__stat"><span class="step-extract__stat-num">{{ totalProps }}</span> 属性</div>
        <div class="step-extract__stat"><span class="step-extract__stat-num">{{ result.relations.length }}</span> 关系</div>
      </div>

      <div class="step-extract__entities">
        <div v-for="e in result.entities" :key="e.name" class="step-extract__entity-card">
          <div class="step-extract__entity-header">
            <span class="step-extract__entity-icon">◉</span>
            <strong>{{ e.displayName }}</strong>
            <span class="step-extract__entity-name">{{ e.name }}</span>
            <span class="step-extract__entity-table">← {{ e.table }}</span>
          </div>
          <div class="step-extract__entity-desc">{{ e.description }}</div>
          <div class="step-extract__entity-props">
            <span v-for="p in e.properties" :key="p.name" class="step-extract__prop-tag">
              {{ p.displayName || p.name }} <small>({{ p.type }})</small>
            </span>
          </div>
        </div>
      </div>

      <div class="step-extract__relations" v-if="result.relations.length">
        <h3 style="font-size:14px;margin-bottom:8px">关系</h3>
        <div v-for="r in result.relations" :key="r.name" class="step-extract__relation-item">
          {{ r.source }} —<strong>{{ r.displayName }}</strong>→ {{ r.target }} ({{ r.cardinality }})
        </div>
      </div>

      <button class="step-extract__btn" @click="emit('next', result)">确认，进入专家审核 →</button>
    </div>

    <div v-if="error" class="step-extract__error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { extractOntologySSE } from '../../../../api/aiBuilderV2'

interface ExtractedProperty { name: string; displayName?: string; type: string; required?: boolean }
interface ExtractedEntity { name: string; displayName: string; table: string; description: string; properties: ExtractedProperty[] }
interface ExtractedRelation { name: string; displayName: string; source: string; target: string; cardinality: string; description?: string }
interface ExtractionResult { entities: ExtractedEntity[]; relations: ExtractedRelation[] }

const props = defineProps<{ tableNames: string[]; documentKeys: string[]; businessDesc: string }>()
const emit = defineEmits<{ (e: 'next', result: ExtractionResult): void }>()

const progressMessages = ref<string[]>([])
const streaming = ref(true)
const result = ref<ExtractionResult | null>(null)
const error = ref('')

const totalProps = computed(() => result.value?.entities.reduce((sum, e) => sum + e.properties.length, 0) || 0)

onMounted(() => {
  const sse = extractOntologySSE(props.tableNames, props.documentKeys, props.businessDesc) as any

  sse.addEventListener('message', (ev: CustomEvent) => {
    const data = ev.detail
    if (data.event === 'progress') {
      progressMessages.value.push(data.message)
    } else if (data.event === 'result') {
      result.value = data.data
      streaming.value = false
    }
  })

  sse.addEventListener('done', () => {
    streaming.value = false
  })

  sse.addEventListener('error', () => {
    error.value = '请求失败，请重试'
    streaming.value = false
  })
})
</script>

<style scoped>
.step-extract { max-width: 900px; margin: 0 auto; padding: 24px; }
.step-extract__title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.step-extract__sub { font-size: 13px; color: #666; margin-bottom: 16px; }
.step-extract__progress { margin-bottom: 20px; }
.step-extract__progress-item { font-size: 13px; color: #2e7d32; padding: 4px 0; }
.step-extract__progress-item--active { color: #4a6fa5; animation: pulse 1.2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.step-extract__stats { display: flex; gap: 24px; margin-bottom: 20px; }
.step-extract__stat { font-size: 13px; color: #666; }
.step-extract__stat-num { font-size: 24px; font-weight: 700; color: #1a1a2e; margin-right: 4px; }
.step-extract__entities { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
.step-extract__entity-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; }
.step-extract__entity-header { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.step-extract__entity-icon { color: #e5b000; }
.step-extract__entity-name { font-family: monospace; font-size: 12px; color: #888; }
.step-extract__entity-table { font-size: 11px; color: #4a6fa5; margin-left: auto; }
.step-extract__entity-desc { font-size: 12px; color: #666; margin-top: 4px; }
.step-extract__entity-props { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.step-extract__prop-tag { font-size: 11px; background: #f0f0f0; padding: 2px 8px; border-radius: 4px; }
.step-extract__relations { margin-bottom: 20px; }
.step-extract__relation-item { font-size: 13px; padding: 4px 0; color: #444; }
.step-extract__btn { padding: 10px 24px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-extract__btn:hover { background: #3d5f8c; }
.step-extract__error { color: #d32f2f; margin-top: 16px; font-size: 13px; }
</style>
