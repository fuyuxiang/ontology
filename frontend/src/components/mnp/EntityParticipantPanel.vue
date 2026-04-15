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
.entity-panel { flex: 1; background: #fff; border-radius: 10px; border: 1px solid #e9ecef; display: flex; flex-direction: column; overflow: hidden; }
.entity-panel__header { display: flex; align-items: center; gap: 8px; padding: 12px 14px; border-bottom: 1px solid #f1f3f5; }
.entity-panel__title { font-size: 14px; font-weight: 600; color: #343a40; }
.entity-panel__sub { font-size: 12px; color: #4c6ef5; background: #eef2ff; padding: 2px 8px; border-radius: 4px; }
.entity-panel__body { flex: 1; overflow-y: auto; padding: 14px; }
.entity-panel__empty { flex: 1; display: flex; align-items: center; justify-content: center; color: #adb5bd; font-size: 14px; }
.entity-section { margin-bottom: 12px; }
.section-label { font-size: 11px; font-weight: 600; color: #868e96; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.entity-cards { display: flex; flex-wrap: wrap; gap: 8px; }
.entity-card { padding: 10px 12px; border-radius: 8px; border: 1px solid #e9ecef; min-width: 160px; flex: 1; }
.entity-card--input { border-left: 3px solid #339af0; }
.entity-card--output { border-left: 3px solid #12b886; }
.entity-card__name { font-size: 13px; font-weight: 600; color: #343a40; }
.entity-card__en { font-size: 11px; color: #868e96; font-family: monospace; }
.entity-card__role { font-size: 10px; color: #4c6ef5; margin-top: 4px; }
.entity-card__attrs { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.attr-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; background: #e7f5ff; color: #1c7ed6; }
.attr-tag--valued { background: #e7f5ff; padding: 2px 8px; }
.attr-val { color: #212529; font-weight: 600; font-size: 10px; }
.attr-tag--out { background: #e6fcf5; color: #0ca678; }
.flow-arrow { display: flex; align-items: center; gap: 8px; justify-content: center; padding: 4px 0; }
.flow-label { font-size: 11px; color: #4c6ef5; font-weight: 500; }
</style>
