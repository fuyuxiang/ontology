<template>
  <div class="node-panel-overlay" @click.self="$emit('close')">
    <div class="node-panel">
      <button class="node-panel__close" @click="$emit('close')">&times;</button>
      <div class="node-panel__header">
        <img class="node-panel__icon" :src="node.icon" alt="" />
        <div>
          <div class="node-panel__name">{{ node.label }}</div>
          <div class="node-panel__desc">{{ node.desc }}</div>
        </div>
      </div>

      <div class="node-panel__grid">
        <div class="node-panel__stat">
          <div class="stat-val">{{ node.tier }}</div>
          <div class="stat-lbl">Tier</div>
        </div>
        <div class="node-panel__stat">
          <div class="stat-val" :class="'status--' + node.status">{{ node.status }}</div>
          <div class="stat-lbl">状态</div>
        </div>
        <div class="node-panel__stat">
          <div class="stat-val">{{ node.relationCount }}</div>
          <div class="stat-lbl">关系</div>
        </div>
        <div class="node-panel__stat">
          <div class="stat-val">{{ node.ruleCount }}</div>
          <div class="stat-lbl">规则</div>
        </div>
        <div class="node-panel__stat">
          <div class="stat-val">{{ node.attrCount }}</div>
          <div class="stat-lbl">属性</div>
        </div>
        <div class="node-panel__stat">
          <div class="stat-val">{{ node.actionCount }}</div>
          <div class="stat-lbl">动作</div>
        </div>
      </div>

      <div v-if="relations.length" class="node-panel__section">
        <div class="section-title">关联关系</div>
        <div v-for="r in relations.slice(0, 8)" :key="r.id" class="rel-row">
          <span class="rel-name">{{ r.name.replaceAll('_', ' ') }}</span>
          <span class="rel-card">{{ r.cardinality }}</span>
        </div>
      </div>

      <div class="node-panel__actions">
        <button class="panel-btn" @click="goDetail">查看详情</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { RelationData } from '../../../api/relations'

const props = defineProps<{
  node: { id: string; label: string; desc: string; icon: string; tier: number; status: string; relationCount: number; ruleCount: number; attrCount: number; actionCount: number }
  relations: RelationData[]
}>()
defineEmits<{ close: [] }>()

const router = useRouter()
function goDetail() { router.push(`/ontology/${props.node.id}`) }
</script>

<style scoped>
.node-panel-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: flex-end;
  padding-right: 24px;
}
.node-panel {
  width: 340px; max-height: 80vh; overflow-y: auto;
  background: rgba(0, 18, 68, 0.95);
  border: 1px solid rgba(0, 80, 234, 0.4);
  border-radius: 12px;
  padding: 24px;
  color: #e8f0ff;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
}
.node-panel__close {
  position: absolute; top: 12px; right: 16px;
  background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer;
}
.node-panel__close:hover { color: #e8f0ff; }
.node-panel__header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.node-panel__icon { width: 48px; height: auto; }
.node-panel__name { font-size: 16px; font-weight: 700; }
.node-panel__desc { font-size: 12px; color: rgba(200, 220, 255, 0.6); margin-top: 2px; }

.node-panel__grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
  margin-bottom: 20px;
}
.node-panel__stat {
  text-align: center;
  background: rgba(0, 50, 145, 0.2);
  border: 1px solid rgba(0, 80, 234, 0.15);
  border-radius: 8px;
  padding: 10px 4px;
}
.stat-val { font-size: 18px; font-weight: 800; color: #5c9aff; }
.stat-lbl { font-size: 10px; color: rgba(200, 220, 255, 0.5); margin-top: 2px; }
.status--active { color: #20c997; }
.status--warning { color: #f59f00; }
.status--error { color: #fa5252; }

.node-panel__section { margin-bottom: 16px; }
.section-title { font-size: 11px; font-weight: 700; color: rgba(200, 220, 255, 0.5); letter-spacing: .08em; text-transform: uppercase; margin-bottom: 8px; }
.rel-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 12px; }
.rel-name { color: rgba(200, 220, 255, 0.85); }
.rel-card { color: #5c9aff; font-size: 10px; font-weight: 600; }

.node-panel__actions { margin-top: 16px; }
.panel-btn {
  width: 100%; padding: 10px;
  background: rgba(0, 80, 234, 0.3);
  border: 1px solid rgba(0, 80, 234, 0.5);
  border-radius: 8px;
  color: #e8f0ff; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: background .15s;
}
.panel-btn:hover { background: rgba(0, 80, 234, 0.5); }
</style>
