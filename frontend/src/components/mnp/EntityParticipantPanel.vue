<template>
  <div class="entity-panel">
    <div class="entity-panel__header">
      <span class="entity-panel__title">实体参与</span>
      <span class="entity-panel__sub" v-if="stage">{{ stage.name }}</span>
    </div>
    <div v-if="stage" class="entity-panel__body">
      <!-- 输入实体 -->
      <div class="entity-section" v-if="stage.inputEntities.length">
        <div class="section-label">输入实体</div>
        <div class="entity-cards">
          <div v-for="e in stage.inputEntities" :key="e.entityName" class="entity-card entity-card--input">
            <div class="entity-card__name">{{ e.entityNameCn }}</div>
            <div class="entity-card__en">{{ e.entityName }}</div>
            <div class="entity-card__role">{{ e.role }}</div>
            <div class="entity-card__attrs">
              <span v-for="a in e.attributes" :key="a" class="attr-tag" :class="{ 'attr-tag--valued': e.values?.[a] !== undefined }">
                {{ a }}<template v-if="e.values?.[a] !== undefined">: <strong class="attr-val">{{ e.values[a] }}</strong></template>
              </span>
            </div>
          </div>
        </div>
      </div>
      <!-- 数据流向 -->
      <div class="flow-arrow" v-if="stage.inputEntities.length && stage.outputEntities.length">
        <svg width="24" height="40" viewBox="0 0 24 40"><path d="M12 4v28M6 26l6 6 6-6" stroke="#4c6ef5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>
        <span class="flow-label">数据流转</span>
      </div>
      <!-- 输出实体 -->
      <div class="entity-section" v-if="stage.outputEntities.length">
        <div class="section-label">输出实体</div>
        <div class="entity-cards">
          <div v-for="e in stage.outputEntities" :key="e.entityName" class="entity-card entity-card--output">
            <div class="entity-card__name">{{ e.entityNameCn }}</div>
            <div class="entity-card__en">{{ e.entityName }}</div>
            <div class="entity-card__role">{{ e.role }}</div>
            <div class="entity-card__attrs">
              <span v-for="a in e.attributes" :key="a" class="attr-tag attr-tag--out">{{ a }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="entity-panel__empty">选择左侧流程阶段查看实体参与详情</div>
  </div>
</template>

<script setup lang="ts">
import type { ProcessStage } from '../../views/scene/MnpWorkbench.vue'
defineProps<{ stage: ProcessStage | null }>()
</script>

<style scoped>
.entity-panel { flex: 1; background: var(--neutral-0); border-radius: 10px; border: 1px solid var(--neutral-200); display: flex; flex-direction: column; overflow: hidden; }
.entity-panel__header { display: flex; align-items: center; gap: 8px; padding: 12px 14px; border-bottom: 1px solid var(--neutral-100); }
.entity-panel__title { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.entity-panel__sub { font-size: var(--text-code-size); color: var(--semantic-600); background: var(--semantic-50); padding: 2px 8px; border-radius: 4px; }
.entity-panel__body { flex: 1; overflow-y: auto; padding: 14px; }
.entity-panel__empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--neutral-500); font-size: var(--text-body-size); }
.entity-section { margin-bottom: 12px; }
.section-label { font-size: var(--text-caption-size); font-weight: 600; color: var(--neutral-600); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.entity-cards { display: flex; flex-wrap: wrap; gap: 8px; }
.entity-card { padding: 10px 12px; border-radius: 8px; border: 1px solid var(--neutral-200); min-width: 160px; flex: 1; }
.entity-card--input { border-left: 3px solid var(--status-info); }
.entity-card--output { border-left: 3px solid var(--status-success); }
.entity-card__name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.entity-card__en { font-size: var(--text-caption-size); color: var(--neutral-600); font-family: var(--font-mono); }
.entity-card__role { font-size: var(--text-caption-upper-size); color: var(--semantic-600); margin-top: 4px; }
.entity-card__attrs { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.attr-tag { font-size: var(--text-caption-upper-size); padding: 1px 6px; border-radius: 3px; background: var(--status-info-bg); color: var(--status-info); }
.attr-tag--valued { background: var(--status-info-bg); padding: 2px 8px; }
.attr-val { color: var(--neutral-900); font-weight: 600; font-size: var(--text-caption-upper-size); }
.attr-tag--out { background: var(--status-success-bg); color: var(--dynamic-700); }
.flow-arrow { display: flex; align-items: center; gap: 8px; justify-content: center; padding: 4px 0; }
.flow-label { font-size: var(--text-caption-size); color: var(--semantic-600); font-weight: 500; }
</style>
