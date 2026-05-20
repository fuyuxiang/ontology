<template>
  <div
    class="asset-card"
    :class="{ 'asset-card--subscribed': asset.subscribed }"
    draggable="true"
    @click="$emit('toggle', asset.id)"
  >
    <div class="asset-card__row">
      <div class="asset-card__icon" :class="`asset-card__icon--${asset.category}`">
        {{ asset.fileType?.toUpperCase().slice(0, 3) || 'ICO' }}
      </div>
      <div class="asset-card__main">
        <div class="asset-card__name">{{ asset.name }}</div>
        <div class="asset-card__meta">{{ asset.type }} · {{ asset.fileSize }} · {{ asset.ontologyTarget }}</div>
      </div>
      <div class="asset-card__check">
        <svg v-if="asset.subscribed" width="14" height="14" viewBox="0 0 14 14">
          <path d="M3 7l3 3 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </svg>
      </div>
    </div>
    <div class="asset-card__desc">{{ asset.description }}</div>
    <div v-if="asset.fields?.length" class="asset-card__fields">
      <span v-for="f in asset.fields.slice(0, 4)" :key="f.name" class="field-tag">
        {{ f.name }}{{ f.en ? ' / ' + f.en : '' }}
      </span>
    </div>
    <div v-if="asset.distilledRules?.length" class="asset-card__rules">
      <div v-for="(r, i) in asset.distilledRules.slice(0, 2)" :key="i" class="rule-line">· {{ r }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DataAsset } from '../../../../types/builder'
defineProps<{ asset: DataAsset }>()
defineEmits<{ (e: 'toggle', id: string): void }>()
</script>

<style scoped>
.asset-card {
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  cursor: pointer;
  transition: all 150ms ease;
}
.asset-card:hover { border-color: #c7d2fe; transform: translateY(-1px); box-shadow: 0 6px 14px -6px rgba(15, 23, 42, 0.08); }
.asset-card--subscribed { border-color: #4f46e5; background: rgba(79, 70, 229, 0.04); }

.asset-card__row { display: flex; align-items: center; gap: 10px; }
.asset-card__icon {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 10px; font-weight: 700;
  flex-shrink: 0;
}
.asset-card__icon--structured { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.asset-card__icon--unstructured { background: linear-gradient(135deg, #f59e0b, #ea580c); }
.asset-card__icon--image { background: linear-gradient(135deg, #06b6d4, #0891b2); }
.asset-card__main { flex: 1; min-width: 0; }
.asset-card__name { font-size: 12px; font-weight: 600; color: #0f172a; }
.asset-card__meta { font-size: 10px; color: #94a3b8; margin-top: 2px; }
.asset-card__check {
  width: 20px; height: 20px; border-radius: 50%;
  border: 1.5px solid #cbd5e1; color: transparent;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: all 150ms ease;
}
.asset-card--subscribed .asset-card__check { background: #4f46e5; border-color: #4f46e5; color: #fff; }
.asset-card__desc {
  margin-top: 8px; font-size: 11px; color: #64748b; line-height: 1.6;
}
.asset-card__fields { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px; }
.field-tag {
  padding: 2px 6px; border-radius: 4px;
  background: #f1f5f9; color: #475569;
  font-size: 10px;
}
.asset-card__rules { margin-top: 6px; padding-top: 6px; border-top: 1px dashed #e2e8f0; }
.rule-line { font-size: 11px; color: #94a3b8; line-height: 1.6; }
</style>
