<template>
  <nav class="ontology-breadcrumb">
    <template v-for="(item, i) in items" :key="i">
      <span
        class="ontology-breadcrumb__item"
        :class="{ 'ontology-breadcrumb__item--current': i === items.length - 1 }"
        @click="item.path && router.push(item.path)"
      >
        <span v-if="item.tier" class="ontology-breadcrumb__tier-tag" :class="`tier${item.tier}`">
          Tier {{ item.tier }}
        </span>
        {{ item.label }}
      </span>
      <span v-if="i < items.length - 1" class="ontology-breadcrumb__sep">›</span>
    </template>
  </nav>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

interface BreadcrumbItem {
  label: string
  path?: string
  tier?: 1 | 2 | 3
}

defineProps<{ items: BreadcrumbItem[] }>()
const router = useRouter()
</script>

<style scoped>
.ontology-breadcrumb {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: var(--text-code-size);
  color: var(--neutral-600);
}

.ontology-breadcrumb__item {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: color var(--transition-fast);
  padding: 2px 4px;
  border-radius: var(--radius-sm);
}
.ontology-breadcrumb__item:hover {
  color: var(--semantic-500);
}
.ontology-breadcrumb__item--current {
  color: var(--neutral-800);
  font-weight: 500;
  cursor: default;
}
.ontology-breadcrumb__item--current:hover {
  color: var(--neutral-800);
}

.ontology-breadcrumb__sep {
  color: var(--neutral-400);
  margin: 0 2px;
  font-size: var(--text-caption-size);
}

.ontology-breadcrumb__tier-tag {
  display: inline-block;
  font-size: var(--text-caption-upper-size);
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
}
.tier1 { background: var(--tier1-bg); color: var(--tier1-text); }
.tier2 { background: var(--tier2-bg); color: var(--tier2-text); }
.tier3 { background: var(--tier3-bg); color: var(--tier3-text); }
</style>
