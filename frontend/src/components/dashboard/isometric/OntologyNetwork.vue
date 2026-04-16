<template>
  <div class="onto-network">
    <svg
      v-if="relations.length > 0"
      class="onto-network__links"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <line
        v-for="rel in renderedRelations"
        :key="rel.id"
        class="onto-link"
        :class="{ 'onto-link--highlighted': rel.highlighted }"
        :x1="rel.x1" :y1="rel.y1" :x2="rel.x2" :y2="rel.y2"
      />
    </svg>

    <template v-if="positionedNodes.length > 0">
      <button
        v-for="node in positionedNodes"
        :key="node.key"
        type="button"
        class="onto-node"
        :class="[
          `onto-node--${node.tone}`,
          {
            'onto-node--selected': selectedKey === node.key,
            'onto-node--muted': node.muted,
            'onto-node--emphasis': node.emphasis,
          },
        ]"
        :style="{ left: `${node.x}%`, top: `${node.y}%` }"
        @click="$emit('select', node.key)"
      >
        <span class="onto-node__icon" v-html="nodeIcon(node.iconType)"></span>
        <span class="onto-node__label">{{ node.displayName }}</span>
        <span class="onto-node__meta">{{ node.entity.relation_count }} 关系 · {{ node.entity.rule_count }} 规则</span>
      </button>

      <div
        v-for="badge in visibleBadges"
        :key="`badge-${badge.id}`"
        class="relation-badge"
        :style="{ left: `${badge.midX}%`, top: `${badge.midY}%` }"
      >
        {{ badge.label }}
      </div>
    </template>

    <div v-else class="onto-network__empty">
      看板当前没有可视化实体。导入对象后，这里会自动生成可点击节点。
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'

type StageId = 'hydrate' | 'activate' | 'wield'
type Tone = 'semantic' | 'dynamic' | 'kinetic'

export interface PositionedNode {
  key: string
  entity: EntityListItem
  x: number
  y: number
  tone: Tone
  stageAffinity: StageId[]
  emphasis: boolean
  muted: boolean
  displayName: string
  iconType: string
}

const props = defineProps<{
  entities: EntityListItem[]
  relations: RelationData[]
  activeStage: StageId
  selectedKey: string
}>()

defineEmits<{ select: [key: string] }>()

const relationLabelMap: Record<string, string> = {
  user_queries_portability: '发起携转查询',
  user_bindto_contract: '绑定合约',
  user_bindto_billing: '同步月账单',
  user_bindto_arrears: '关联欠费状态',
  user_has_voice_calls: '连接通话详单',
  user_receives_retention: '产生维系记录',
  user_bindto_convergence: '绑定融合套餐',
  contract_restricts_portability: '限制携转资格',
  arrears_restricts_portability: '欠费拦截携转',
  complaint_influences_retention: '投诉驱动挽留',
  user_has_complaints: '触发投诉工单',
}

const layoutSlots = [
  { x: 50, y: 50 }, { x: 29, y: 28 }, { x: 72, y: 28 },
  { x: 18, y: 50 }, { x: 82, y: 50 }, { x: 29, y: 72 },
  { x: 72, y: 72 }, { x: 50, y: 16 }, { x: 50, y: 84 },
]

const toneSequence: Tone[] = ['dynamic', 'semantic', 'kinetic', 'semantic', 'dynamic', 'kinetic', 'semantic', 'dynamic', 'kinetic']
const iconTypes = ['person', 'factory', 'truck', 'building', 'gear', 'document', 'phone', 'shield', 'chart']

const entityDegree = computed(() => {
  const map = new Map<string, number>()
  for (const r of props.relations) {
    map.set(r.from_entity_id, (map.get(r.from_entity_id) ?? 0) + 1)
    map.set(r.to_entity_id, (map.get(r.to_entity_id) ?? 0) + 1)
  }
  return map
})

const positionedNodes = computed<PositionedNode[]>(() => {
  const sorted = [...props.entities]
    .sort((a, b) => {
      const da = entityDegree.value.get(a.id) ?? 0
      const db = entityDegree.value.get(b.id) ?? 0
      if (db !== da) return db - da
      if (b.relation_count !== a.relation_count) return b.relation_count - a.relation_count
      return b.rule_count - a.rule_count
    })
    .slice(0, 9)

  return sorted.map((entity, i) => {
    const slot = layoutSlots[i] ?? layoutSlots[0]
    const tone = entity.status === 'active' ? toneSequence[i] : entity.status === 'warning' ? 'kinetic' as Tone : 'semantic' as Tone
    const stageAffinity: StageId[] = i === 0
      ? ['hydrate', 'activate', 'wield']
      : i < 4 ? ['activate', 'wield'] : ['activate']

    return {
      key: `entity:${entity.id}`,
      entity,
      x: slot.x,
      y: slot.y,
      tone,
      stageAffinity,
      emphasis: i === 0 || entity.rule_count > 0 || entity.relation_count > 2,
      muted: !stageAffinity.includes(props.activeStage),
      displayName: entity.name_cn || entity.name,
      iconType: iconTypes[i % iconTypes.length],
    }
  })
})

function formatRelationLabel(name: string) {
  return relationLabelMap[name] ?? name.replaceAll('_', ' ')
}

const renderedRelations = computed(() => {
  const posMap = new Map(positionedNodes.value.map(n => [n.entity.id, n]))
  const selId = props.selectedKey.startsWith('entity:') ? props.selectedKey.slice(7) : null
  const centerId = positionedNodes.value[0]?.entity.id ?? null

  return props.relations
    .filter(r => posMap.has(r.from_entity_id) && posMap.has(r.to_entity_id))
    .map((r, i) => {
      const from = posMap.get(r.from_entity_id)!
      const to = posMap.get(r.to_entity_id)!
      const highlighted = selId
        ? r.from_entity_id === selId || r.to_entity_id === selId
        : r.from_entity_id === centerId || r.to_entity_id === centerId || props.activeStage === 'activate'
      return {
        id: r.id,
        label: formatRelationLabel(r.name),
        x1: from.x, y1: from.y, x2: to.x, y2: to.y,
        midX: (from.x + to.x) / 2,
        midY: (from.y + to.y) / 2 + (i % 2 === 0 ? -2.5 : 2.5),
        highlighted,
      }
    })
})

const visibleBadges = computed(() => {
  const hl = renderedRelations.value.filter(r => r.highlighted)
  return hl.slice(0, props.selectedKey.startsWith('entity:') ? 5 : 3)
})

function nodeIcon(type: string): string {
  const icons: Record<string, string> = {
    person: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="3" stroke="currentColor" stroke-width="1.2"/><path d="M2 14c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    factory: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M1 14V6l4 3V6l4 3V4h6v10H1z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>',
    truck: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="4" width="9" height="8" rx="1" stroke="currentColor" stroke-width="1.2"/><path d="M10 7h3l2 3v2h-5V7z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><circle cx="4" cy="13" r="1.5" stroke="currentColor" stroke-width="1"/><circle cx="12.5" cy="13" r="1.5" stroke="currentColor" stroke-width="1"/></svg>',
    building: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="3" y="1" width="10" height="14" rx="1" stroke="currentColor" stroke-width="1.2"/><rect x="5" y="3" width="2" height="2" fill="currentColor" rx="0.5"/><rect x="9" y="3" width="2" height="2" fill="currentColor" rx="0.5"/><rect x="5" y="7" width="2" height="2" fill="currentColor" rx="0.5"/><rect x="9" y="7" width="2" height="2" fill="currentColor" rx="0.5"/><rect x="6.5" y="11" width="3" height="4" fill="currentColor" rx="0.5"/></svg>',
    gear: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2.5" stroke="currentColor" stroke-width="1.2"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    document: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 1h5l4 4v10H4V1z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><path d="M9 1v4h4M6 8h4M6 11h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    phone: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="4" y="1" width="8" height="14" rx="2" stroke="currentColor" stroke-width="1.2"/><circle cx="8" cy="12" r="1" fill="currentColor"/></svg>',
    shield: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1L2 4v4c0 3.5 2.5 6.5 6 7.5 3.5-1 6-4 6-7.5V4L8 1z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>',
    chart: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="9" width="3" height="6" rx="0.5" stroke="currentColor" stroke-width="1.2"/><rect x="6.5" y="5" width="3" height="10" rx="0.5" stroke="currentColor" stroke-width="1.2"/><rect x="12" y="1" width="3" height="14" rx="0.5" stroke="currentColor" stroke-width="1.2"/></svg>',
  }
  return icons[type] ?? icons.gear
}
</script>

<style scoped>
.onto-network {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 240px;
}

.onto-network__links {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.onto-link {
  stroke: rgba(15, 17, 23, 0.16);
  stroke-width: 0.38;
  stroke-dasharray: 1.8 1.8;
}

.onto-link--highlighted {
  stroke: rgba(18, 184, 134, 0.74);
  stroke-width: 0.7;
  stroke-dasharray: none;
}

.onto-node {
  position: absolute;
  width: 118px;
  min-height: 58px;
  padding: 8px 10px;
  border-radius: 16px;
  border: 1px solid rgba(15, 17, 23, 0.08);
  background: rgba(255, 255, 255, 0.92);
  transform: translate(-50%, -50%);
  cursor: pointer;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  text-align: center;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast),
    opacity var(--transition-fast), border-color var(--transition-fast);
  box-shadow: 0 8px 22px rgba(15, 17, 23, 0.08);
}

.onto-node:hover {
  transform: translate(-50%, calc(-50% - 3px));
  box-shadow: 0 14px 28px rgba(15, 17, 23, 0.12);
}

.onto-node--selected {
  border-color: rgba(18, 184, 134, 0.3);
  box-shadow: 0 16px 32px rgba(18, 184, 134, 0.16);
}

.onto-node--muted { opacity: 0.35; }
.onto-node--emphasis { width: 128px; }

.onto-node--semantic { background: rgba(238, 242, 255, 0.92); }
.onto-node--dynamic { background: rgba(230, 252, 245, 0.94); }
.onto-node--kinetic { background: rgba(255, 248, 225, 0.94); }

.onto-node__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  color: var(--neutral-600);
}

.onto-node__label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--neutral-800);
}

.onto-node__meta {
  display: block;
  font-size: 9px;
  color: var(--neutral-500);
}

.relation-badge {
  position: absolute;
  transform: translate(-50%, -50%);
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(18, 184, 134, 0.12);
  border: 1px solid rgba(18, 184, 134, 0.18);
  color: var(--dynamic-800);
  font-size: 9px;
  font-weight: 600;
  white-space: nowrap;
  z-index: 3;
  pointer-events: none;
  box-shadow: 0 6px 14px rgba(18, 184, 134, 0.1);
}

.onto-network__empty {
  position: absolute;
  inset: 20% 15%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  text-align: center;
  border-radius: 20px;
  border: 1px dashed var(--neutral-300);
  color: var(--neutral-500);
  background: rgba(255, 255, 255, 0.78);
}

@media (max-width: 980px) {
  .onto-node { width: 100px; }
}

@media (max-width: 720px) {
  .relation-badge { display: none; }
}
</style>
