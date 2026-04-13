<template>
  <div class="canvas-page">
    <div class="canvas-page__header">
      <div>
        <h1 class="text-display">关系画布</h1>
        <p class="text-caption" style="margin-top: 4px;">本体对象关系全景图 · 点击节点查看详情</p>
      </div>
    </div>

    <PageState :loading="store.loading && nodes.length === 0" :empty="!store.loading && nodes.length === 0" text="加载关系图谱..." empty-text="暂无本体数据">

    <div class="canvas-page__body">
      <!-- 节点图 -->
      <div class="canvas-page__graph">
        <div class="canvas-page__tier-section" v-for="group in tierGroups" :key="group.tier">
          <div class="canvas-page__tier-label text-caption-upper">
            Tier {{ group.tier }} {{ group.name }}
          </div>
          <div class="canvas-page__nodes">
            <div
              v-for="node in group.nodes"
              :key="node.id"
              class="canvas-node"
              :class="[
                `canvas-node--tier${node.tier}`,
                selectedId === node.id ? 'canvas-node--selected' : ''
              ]"
              @click="selectNode(node.id)"
            >
              <span class="canvas-node__badge" :style="{ background: `var(--tier${node.tier}-primary)` }">
                T{{ node.tier }}
              </span>
              <div class="canvas-node__info">
                <span class="canvas-node__name">{{ node.name }}</span>
                <span class="canvas-node__cn">{{ node.nameCn }}</span>
              </div>
              <span class="canvas-node__count">{{ node.relCount }} 关系</span>
            </div>
          </div>
        </div>

        <!-- 关系连线列表 -->
        <div class="canvas-page__relations">
          <h3 class="text-h3" style="margin-bottom: 12px;">
            关系连线
            <span class="text-caption" style="margin-left: 8px;">共 {{ displayRelations.length }} 条</span>
          </h3>
          <div class="relation-cards">
            <div
              v-for="(rel, i) in displayRelations"
              :key="i"
              class="relation-card"
              :class="{ 'relation-card--highlight': selectedId === rel.fromId || selectedId === rel.toId }"
            >
              <span class="relation-card__from">{{ rel.from }}</span>
              <div class="relation-card__line">
                <span class="relation-card__label">{{ rel.label }}</span>
                <span class="relation-card__cardinality">{{ rel.cardinality }}</span>
              </div>
              <span class="relation-card__to">{{ rel.to }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧详情面板 -->
      <div v-if="selectedNode" class="canvas-page__panel">
        <div class="panel-header">
          <span class="canvas-node__badge" :style="{ background: `var(--tier${selectedNode.tier}-primary)` }">T{{ selectedNode.tier }}</span>
          <div>
            <div class="text-h3">{{ selectedNode.name }}</div>
            <div class="text-caption">{{ selectedNode.nameCn }}</div>
          </div>
        </div>
        <div class="panel-section">
          <div class="panel-label text-caption-upper">关系 ({{ nodeRelations.length }})</div>
          <div class="panel-rel" v-for="(r, i) in nodeRelations" :key="i">
            <span class="text-body-medium">{{ r.label }}</span>
            <span class="text-caption">→ {{ r.to }}</span>
            <span class="relation-card__cardinality">{{ r.cardinality }}</span>
          </div>
        </div>
        <button class="panel-detail-btn" @click="$router.push(`/ontology/${selectedNode.id}`)">
          查看完整详情 →
        </button>
      </div>
    </div>
    </PageState>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useOntologyStore } from '../../store/ontology'
import PageState from '../../components/common/PageState.vue'

const store = useOntologyStore()
const selectedId = ref<string | null>(null)

onMounted(async () => {
  if (store.entities.length === 0) await store.fetchEntities()
  await store.fetchGraph()
})

interface Node { id: string; name: string; nameCn: string; tier: 1 | 2 | 3; relCount: number }
interface Relation { fromId: string; from: string; toId: string; to: string; label: string; cardinality: string }

const nodes = computed<Node[]>(() =>
  store.graphData?.nodes.map(n => ({
    id: n.id, name: n.name, nameCn: n.name_cn,
    tier: n.tier as 1 | 2 | 3, relCount: n.relation_count,
  })) ?? []
)

const allRelations = computed<Relation[]>(() =>
  store.graphData?.edges.map(e => ({
    fromId: e.from_id, from: e.from_name,
    toId: e.to_id, to: e.to_name,
    label: e.label, cardinality: e.cardinality,
  })) ?? []
)

const tierGroups = computed(() => [
  { tier: 1, name: '核心对象', nodes: nodes.value.filter(n => n.tier === 1) },
  { tier: 2, name: '领域对象', nodes: nodes.value.filter(n => n.tier === 2) },
  { tier: 3, name: '场景对象', nodes: nodes.value.filter(n => n.tier === 3) },
])

const displayRelations = computed(() => {
  if (!selectedId.value) return allRelations.value
  return allRelations.value.filter(r => r.fromId === selectedId.value || r.toId === selectedId.value)
})

const selectedNode = computed(() => nodes.value.find(n => n.id === selectedId.value) ?? null)

const nodeRelations = computed(() => {
  if (!selectedId.value) return []
  return allRelations.value
    .filter(r => r.fromId === selectedId.value || r.toId === selectedId.value)
    .map(r => ({
      label: r.label,
      to: r.fromId === selectedId.value ? r.to : r.from,
      cardinality: r.cardinality,
    }))
})

function selectNode(id: string) {
  selectedId.value = selectedId.value === id ? null : id
}
</script>

<style scoped>
.canvas-page { padding: 0; }
.canvas-page__header { padding: 24px 24px 0; }
.canvas-page__body { display: flex; gap: 20px; padding: 20px 24px; }
.canvas-page__graph { flex: 1; }

.canvas-page__tier-section { margin-bottom: 20px; }
.canvas-page__tier-label { margin-bottom: 8px; }
.canvas-page__nodes { display: flex; flex-wrap: wrap; gap: 10px; }

.canvas-node {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; border-radius: var(--radius-md);
  border: 1px solid var(--neutral-200); background: var(--neutral-0);
  cursor: pointer; transition: all 200ms ease; min-width: 160px;
}
.canvas-node:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.canvas-node--selected { box-shadow: var(--shadow-glow-semantic); border-color: var(--semantic-400); }
.canvas-node--tier1:hover { border-color: var(--tier1-primary); }
.canvas-node--tier2:hover { border-color: var(--tier2-primary); }
.canvas-node--tier3:hover { border-color: var(--tier3-primary); }

.canvas-node__badge {
  width: 22px; height: 22px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.canvas-node__info { flex: 1; display: flex; flex-direction: column; }
.canvas-node__name { font-size: 13px; font-weight: 500; color: var(--neutral-800); }
.canvas-node__cn { font-size: 11px; color: var(--neutral-500); }
.canvas-node__count { font-size: 10px; color: var(--neutral-400); white-space: nowrap; }

/* 关系卡片 */
.canvas-page__relations { margin-top: 8px; }
.relation-cards { display: flex; flex-direction: column; gap: 6px; }
.relation-card {
  display: flex; align-items: center; gap: 12px; padding: 8px 14px;
  background: var(--neutral-0); border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md); transition: border-color 200ms ease;
}
.relation-card--highlight { border-color: var(--semantic-300); background: var(--semantic-50); }
.relation-card__from, .relation-card__to {
  font-size: 12px; font-weight: 500; color: var(--neutral-800);
  padding: 3px 8px; background: var(--neutral-50); border-radius: var(--radius-sm);
}
.relation-card__line {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  position: relative; min-width: 60px;
}
.relation-card__line::before {
  content: ''; position: absolute; top: 50%; left: 0; right: 0;
  height: 1px; background: var(--semantic-300);
}
.relation-card__line::after {
  content: ''; position: absolute; top: 50%; right: 0;
  transform: translateY(-50%); border: 4px solid transparent;
  border-left-color: var(--semantic-300);
}
.relation-card__label {
  font-size: 10px; font-weight: 500; color: var(--neutral-700);
  background: var(--neutral-0); padding: 0 4px; position: relative; z-index: 1;
}
.relation-card__cardinality {
  font-size: 10px; font-weight: 500; color: var(--neutral-500);
  background: var(--neutral-50); padding: 1px 5px; border-radius: 3px;
  position: relative; z-index: 1;
}

/* 右侧面板 */
.canvas-page__panel {
  width: 280px; flex-shrink: 0; background: var(--neutral-0);
  border: 1px solid var(--neutral-200); border-radius: var(--radius-lg);
  padding: 16px; align-self: flex-start;
}
.panel-header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.panel-section { margin-bottom: 16px; }
.panel-label { margin-bottom: 8px; }
.panel-rel {
  display: flex; align-items: center; gap: 8px; padding: 6px 0;
  border-bottom: 1px solid var(--neutral-100); font-size: 12px;
}
.panel-rel:last-child { border-bottom: none; }
.panel-detail-btn {
  width: 100%; padding: 8px; border-radius: var(--radius-md); border: none;
  background: var(--semantic-600); color: #fff; font-size: 13px;
  font-weight: 500; cursor: pointer; transition: background var(--transition-fast);
}
.panel-detail-btn:hover { background: var(--semantic-700); }
</style>