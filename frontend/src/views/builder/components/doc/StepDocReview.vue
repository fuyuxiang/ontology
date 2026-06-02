<template>
  <div class="step-review">
    <h2 class="step-review__title">本体确认</h2>
    <p class="step-review__sub">共提取 {{ result.entities.length }} 个实体、{{ totalProps }} 个属性、{{ result.relations.length }} 个关系</p>

    <div class="step-review__stats">
      <div class="step-review__stat"><span class="step-review__stat-num">{{ result.entities.length }}</span> 实体</div>
      <div class="step-review__stat"><span class="step-review__stat-num">{{ totalProps }}</span> 属性</div>
      <div class="step-review__stat"><span class="step-review__stat-num">{{ result.relations.length }}</span> 关系</div>
    </div>

    <div class="step-review__entities">
      <div v-for="e in result.entities" :key="e.name" class="step-review__entity-card">
        <div class="step-review__entity-header">
          <span class="step-review__entity-icon">◉</span>
          <strong>{{ e.displayName }}</strong>
          <span class="step-review__entity-name">{{ e.name }}</span>
        </div>
        <div class="step-review__entity-desc" v-if="e.description">{{ e.description }}</div>
        <div class="step-review__entity-props">
          <span v-for="p in e.properties" :key="p.name" class="step-review__prop-tag">
            {{ p.displayName || p.name }} <small>({{ p.type }})</small>
          </span>
        </div>
      </div>
    </div>

    <div class="step-review__relations" v-if="result.relations.length">
      <h3 class="step-review__section-title">关系</h3>
      <div v-for="r in result.relations" :key="r.name" class="step-review__relation-item">
        {{ r.source }} —<strong>{{ r.displayName }}</strong>→ {{ r.target }} ({{ r.cardinality }})
      </div>
    </div>

    <div class="step-review__actions">
      <button class="step-review__btn step-review__btn--back" @click="emit('prev')">← 返回修改</button>
      <button class="step-review__btn" @click="emit('confirm', result)">确认入库</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface OntologyData {
  entities: Array<{ name: string; displayName: string; description?: string; properties: Array<{ name: string; displayName?: string; type: string }> }>
  relations: Array<{ name: string; displayName: string; source: string; target: string; cardinality: string }>
}

const props = defineProps<{ result: OntologyData }>()
const emit = defineEmits<{ (e: 'prev'): void; (e: 'confirm', data: OntologyData): void }>()

const totalProps = computed(() => props.result.entities.reduce((sum, e) => sum + e.properties.length, 0))
</script>

<style scoped>
.step-review { max-width: 900px; margin: 0 auto; padding: 24px; }
.step-review__title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.step-review__sub { font-size: 13px; color: #666; margin-bottom: 16px; }
.step-review__stats { display: flex; gap: 24px; margin-bottom: 20px; }
.step-review__stat { font-size: 13px; color: #666; }
.step-review__stat-num { font-size: 24px; font-weight: 700; color: #1a1a2e; margin-right: 4px; }
.step-review__entities { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
.step-review__entity-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; }
.step-review__entity-header { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.step-review__entity-icon { color: #e5b000; }
.step-review__entity-name { font-family: monospace; font-size: 12px; color: #888; }
.step-review__entity-desc { font-size: 12px; color: #666; margin-top: 4px; }
.step-review__entity-props { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.step-review__prop-tag { font-size: 11px; background: #f0f0f0; padding: 2px 8px; border-radius: 4px; }
.step-review__relations { margin-bottom: 20px; }
.step-review__section-title { font-size: 14px; margin-bottom: 8px; }
.step-review__relation-item { font-size: 13px; padding: 4px 0; color: #444; }
.step-review__actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px; }
.step-review__btn { padding: 10px 24px; background: #2e7d32; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-review__btn:hover { background: #1b5e20; }
.step-review__btn--back { background: transparent; color: #666; border: 1px solid #d0d0d0; }
.step-review__btn--back:hover { background: #f5f5f5; }
</style>
