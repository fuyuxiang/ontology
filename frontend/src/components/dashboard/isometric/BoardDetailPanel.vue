<template>
  <aside class="detail-panel">
    <span class="detail-panel__eyebrow text-caption-upper">{{ meta.eyebrow }}</span>
    <div class="detail-panel__title-row">
      <h3 class="detail-panel__title">{{ meta.title }}</h3>
      <span class="detail-badge" :class="`detail-badge--${meta.badgeTone}`">{{ meta.badge }}</span>
    </div>
    <p class="detail-panel__summary">{{ meta.summary }}</p>

    <div class="detail-panel__facts">
      <div class="detail-fact" v-for="fact in meta.facts" :key="fact.label">
        <span class="detail-fact__label">{{ fact.label }}</span>
        <strong class="detail-fact__value">{{ fact.value }}</strong>
      </div>
    </div>

    <div class="detail-panel__section" v-if="meta.connections.length > 0">
      <span class="detail-panel__section-label">可继续追踪</span>
      <div class="detail-panel__chips">
        <button
          v-for="connection in meta.connections"
          :key="connection.key"
          type="button"
          class="detail-chip"
          @click="$emit('select', connection.key)"
        >
          {{ connection.label }}
        </button>
      </div>
    </div>

    <div class="detail-panel__section" v-if="meta.notes.length > 0">
      <span class="detail-panel__section-label">执行说明</span>
      <ul class="detail-panel__notes">
        <li v-for="note in meta.notes" :key="note">{{ note }}</li>
      </ul>
    </div>

    <div class="detail-panel__actions">
      <button type="button" class="detail-btn detail-btn--primary" @click="$emit('route', meta.primaryRoute)">
        {{ meta.primaryLabel }}
      </button>
      <button type="button" class="detail-btn detail-btn--ghost" @click="$emit('route', meta.secondaryRoute)">
        {{ meta.secondaryLabel }}
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
type Tone = 'semantic' | 'dynamic' | 'kinetic'

export interface DetailMeta {
  eyebrow: string
  title: string
  badge: string
  badgeTone: Tone
  summary: string
  facts: Array<{ label: string; value: string | number }>
  connections: Array<{ key: string; label: string }>
  notes: string[]
  primaryLabel: string
  primaryRoute: string
  secondaryLabel: string
  secondaryRoute: string
}

defineProps<{ meta: DetailMeta }>()
defineEmits<{
  select: [key: string]
  route: [path: string]
}>()
</script>

<style scoped>
.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px;
  border-radius: 24px;
  border: 1px solid rgba(15, 17, 23, 0.06);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 40px rgba(15, 17, 23, 0.06);
}

.detail-panel__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.detail-panel__title {
  font-size: var(--text-h1-size);
  line-height: 1.2;
  color: var(--neutral-900);
}

.detail-badge {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: var(--text-caption-size);
  font-weight: 700;
  white-space: nowrap;
}

.detail-badge--semantic { background: var(--semantic-50); color: var(--semantic-700); }
.detail-badge--dynamic { background: var(--dynamic-50); color: var(--dynamic-800); }
.detail-badge--kinetic { background: var(--kinetic-50); color: var(--kinetic-800); }

.detail-panel__summary {
  font-size: var(--text-body-size);
  line-height: 1.8;
  color: var(--neutral-600);
}

.detail-panel__facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.detail-fact {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 14px;
  border-radius: 16px;
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
}

.detail-fact__label { font-size: var(--text-caption-size); color: var(--neutral-500); }
.detail-fact__value { font-size: var(--text-h3-size); color: var(--neutral-800); }

.detail-panel__section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-panel__section-label {
  font-size: var(--text-caption-size);
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--neutral-500);
  text-transform: uppercase;
}

.detail-panel__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-chip {
  padding: 7px 10px;
  border-radius: 999px;
  border: 1px solid rgba(76, 110, 245, 0.14);
  background: rgba(76, 110, 245, 0.07);
  color: var(--semantic-700);
  font-size: var(--text-code-size);
  cursor: pointer;
  transition: background var(--transition-fast), transform var(--transition-fast), border-color var(--transition-fast);
}

.detail-chip:hover {
  transform: translateY(-1px);
  background: rgba(76, 110, 245, 0.12);
  border-color: rgba(76, 110, 245, 0.2);
}

.detail-panel__notes {
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--neutral-600);
  line-height: 1.7;
}

.detail-panel__actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: auto;
}

.detail-btn {
  padding: 11px 14px;
  border-radius: 14px;
  border: 1px solid transparent;
  font-size: var(--text-body-size);
  font-weight: 600;
  cursor: pointer;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast), background var(--transition-fast);
}

.detail-btn:hover { transform: translateY(-1px); }

.detail-btn--primary {
  background: linear-gradient(135deg, var(--dynamic-700), var(--semantic-600));
  color: var(--neutral-0);
  box-shadow: 0 12px 24px rgba(18, 184, 134, 0.2);
}

.detail-btn--ghost {
  background: rgba(255, 255, 255, 0.82);
  border-color: var(--neutral-200);
  color: var(--neutral-700);
}

@media (max-width: 720px) {
  .detail-panel__facts { grid-template-columns: 1fr; }
}
</style>
