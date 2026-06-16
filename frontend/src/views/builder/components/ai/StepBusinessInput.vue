<template>
  <div class="step-input">
    <h2 class="step-input__title">描述你的业务场景</h2>
    <p class="step-input__sub">输入业务描述，AI 将自动匹配相关的数据主题域</p>
    <textarea class="step-input__textarea" v-model="desc" placeholder="例如：我需要构建宽带退单稽核的本体，包含客户、工单、退单原因等实体..." rows="5"></textarea>
    <button class="step-input__btn" :disabled="!desc.trim() || loading" @click="analyze">
      {{ loading ? '分析中...' : '开始分析' }}
    </button>

    <div v-if="result" class="step-input__result">
      <div class="step-input__result-title">AI 推荐的主题域：</div>
      <div class="step-input__result-reason">{{ result.reason }}</div>
      <div class="step-input__domains">
        <div v-for="d in result.all_domains" :key="d"
             class="step-input__domain-card"
             :class="{ 'step-input__domain-card--selected': selectedDomains.includes(d), 'step-input__domain-card--recommended': result.domains.includes(d) }"
             @click="toggleDomain(d)">
          <span v-if="result.domains.includes(d)" class="step-input__badge">推荐</span>
          {{ d }}
        </div>
      </div>
      <button class="step-input__btn step-input__btn--next" :disabled="!selectedDomains.length" @click="emit('next', { domains: selectedDomains, businessDesc: desc })">
        已选 {{ selectedDomains.length }} 个主题域 → 下一步：选择数据表
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { matchDomain } from '../../../../api/aiBuilderV2'
import type { DomainMatchResult } from '../../../../api/aiBuilderV2'
import { useToast } from '../../../../composables/useToast'

const toast = useToast()

const emit = defineEmits<{ (e: 'next', payload: { domains: string[]; businessDesc: string }): void }>()

const desc = ref('')
const loading = ref(false)
const result = ref<DomainMatchResult | null>(null)
const selectedDomains = ref<string[]>([])

function toggleDomain(d: string) {
  const idx = selectedDomains.value.indexOf(d)
  if (idx >= 0) {
    selectedDomains.value.splice(idx, 1)
  } else {
    selectedDomains.value.push(d)
  }
}

async function analyze() {
  if (!desc.value.trim()) return
  loading.value = true
  try {
    const resp = await matchDomain(desc.value)
    result.value = resp.data
    if (resp.data.domains.length) selectedDomains.value = [...resp.data.domains]
  } catch (e: any) {
    console.error(e)
    toast.error(e?.response?.data?.detail || e?.message || '业务领域匹配失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.step-input { max-width: 720px; margin: 0 auto; padding: 32px 24px; }
.step-input__title { font-size: 20px; font-weight: 600; margin-bottom: 8px; color: #1a1a2e; }
.step-input__sub { font-size: 13px; color: #666; margin-bottom: 16px; }
.step-input__textarea { width: 100%; padding: 12px; border: 1px solid #d0d0d0; border-radius: 8px; font-size: 14px; resize: vertical; font-family: inherit; }
.step-input__textarea:focus { outline: none; border-color: #4a6fa5; }
.step-input__btn { margin-top: 12px; padding: 10px 24px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-input__btn:disabled { opacity: 0.5; cursor: default; }
.step-input__btn:hover:not(:disabled) { background: #3d5f8c; }
.step-input__btn--next { background: #2e7d32; }
.step-input__btn--next:hover:not(:disabled) { background: #1b5e20; }
.step-input__result { margin-top: 24px; padding: 16px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e0e0e0; }
.step-input__result-title { font-weight: 600; margin-bottom: 4px; }
.step-input__result-reason { font-size: 12px; color: #666; margin-bottom: 12px; }
.step-input__domains { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.step-input__domain-card { padding: 8px 16px; border: 1px solid #d0d0d0; border-radius: 6px; cursor: pointer; font-size: 13px; position: relative; }
.step-input__domain-card:hover { border-color: #4a6fa5; }
.step-input__domain-card--selected { border-color: #4a6fa5; background: #e8f0fc; color: #4a6fa5; font-weight: 500; }
.step-input__domain-card--recommended { border-color: #2e7d32; }
.step-input__badge { position: absolute; top: -8px; right: -4px; background: #2e7d32; color: #fff; font-size: 9px; padding: 1px 5px; border-radius: 8px; }
</style>
