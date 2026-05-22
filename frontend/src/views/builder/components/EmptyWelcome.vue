<template>
  <div class="ob-root ob-empty-root">
    <div class="ob-empty-blur ob-empty-blur-top"></div>
    <div class="ob-empty-blur ob-empty-blur-bottom"></div>

    <div class="ob-empty-shell">
      <div class="ob-empty-head">
        <h1>开始构建你的第一个本体</h1>
        <p>选择一种构建方式 — 手工、文件、文档或对话，全程辅助你完成本体设计</p>
      </div>

      <div class="ob-empty-grid ob-empty-grid--four">
        <button
          v-for="m in METHOD_CARDS"
          :key="m.id"
          type="button"
          :class="['ob-empty-card-mini', `ob-empty-card-mini--${m.tone}`]"
          @click="emit('open-method', m.id)"
        >
          <span class="ob-empty-mini-icon" :style="{ background: m.gradient }">{{ m.short }}</span>
          <div class="ob-empty-mini-text">
            <strong>{{ m.title }}</strong>
            <span>{{ m.subtitle }}</span>
            <em>{{ m.audience }}</em>
          </div>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="ob-empty-mini-arrow"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
        </button>
      </div>
    </div>
    <slot name="modal" />
  </div>
</template>

<script setup lang="ts">
import type { BuildMethod } from '../../../types/builder'

const emit = defineEmits<{
  (e: 'open-method', m: BuildMethod): void
}>()

interface Card { id: BuildMethod; short: string; title: string; subtitle: string; audience: string; tone: string; gradient: string }
const METHOD_CARDS: Card[] = [
  { id: 'manual',  short: '手工', title: '手工建模', subtitle: '逐项定义对象、属性、关系',          audience: '适合本体工程师',  tone: 'manual',  gradient: 'linear-gradient(135deg, #6366f1, #4f46e5)' },
  { id: 'import',  short: '导入', title: '文件导入', subtitle: 'OWL / RDF / JSON 标准本体文件',     audience: '适合本体工程师',  tone: 'import',  gradient: 'linear-gradient(135deg, #10b981, #059669)' },
  { id: 'extract', short: '抽取', title: '文档抽取', subtitle: 'Word / Excel / PDF 业务文档 LLM 抽取', audience: '适合业务专家',    tone: 'extract', gradient: 'linear-gradient(135deg, #fb923c, #ea580c)' },
  { id: 'chat',    short: '对话', title: '对话生成', subtitle: '对话式联动数据资产与文档生成',        audience: '适合业务分析师',  tone: 'chat',    gradient: 'linear-gradient(135deg, #8b5cf6, #6366f1)' },
]
</script>

<style scoped>
.ob-empty-grid--four {
  display: grid;
  grid-template-columns: repeat(2, minmax(280px, 1fr));
  gap: 14px;
  width: min(720px, 100%);
}
.ob-empty-card-mini {
  position: relative;
  display: flex; align-items: center; gap: 14px;
  padding: 18px 18px;
  border-radius: 14px;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  cursor: pointer; text-align: left;
  transition: all 150ms ease;
}
.ob-empty-card-mini:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px -10px rgba(15, 23, 42, 0.18);
  border-color: #cbd5e1;
}
.ob-empty-mini-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 14px; flex-shrink: 0;
}
.ob-empty-mini-text { flex: 1; display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.ob-empty-mini-text strong { font-size: 15px; color: #0f172a; font-weight: 600; }
.ob-empty-mini-text span { font-size: 12px; color: #64748b; }
.ob-empty-mini-text em { font-size: 11px; color: #94a3b8; font-style: normal; }
.ob-empty-mini-arrow { flex-shrink: 0; }
.ob-empty-card-mini--manual:hover  { border-color: #6366f1; }
.ob-empty-card-mini--import:hover  { border-color: #10b981; }
.ob-empty-card-mini--extract:hover { border-color: #fb923c; }
.ob-empty-card-mini--chat:hover    { border-color: #8b5cf6; }
</style>
