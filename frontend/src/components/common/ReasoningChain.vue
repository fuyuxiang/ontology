<template>
  <div class="reasoning-chain">
    <div class="reasoning-chain__title">{{ title }}</div>
    <div class="reasoning-chain__steps">
      <div
        v-for="(step, i) in steps"
        :key="i"
        class="reasoning-step"
        :style="{ animationDelay: `${i * 200}ms` }"
      >
        <span class="reasoning-step__index" :class="`reasoning-step__index--${step.type}`">
          {{ stepIndex[step.type] ?? i + 1 }}
        </span>
        <div class="reasoning-step__body">
          <div class="reasoning-step__type" :class="`reasoning-step__type--${step.type}`">
            {{ step.title }}
          </div>
          <span class="reasoning-step__source">{{ step.source }}</span>
          <div class="reasoning-step__result">{{ step.result }}</div>
        </div>
        <div v-if="i < steps.length - 1" class="reasoning-chain__connector" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface ReasoningStep {
  type: 'ontology' | 'ml' | 'rule' | 'output'
  title: string
  source: string
  result: string
}

defineProps<{
  title: string
  steps: ReasoningStep[]
}>()

const stepIndex: Record<string, string> = {
  ontology: '1', ml: '2', rule: '3', output: '4'
}
</script>

<style scoped>
.reasoning-chain {
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-xl);
  background: var(--neutral-0);
  padding: 20px 24px;
}
.reasoning-chain__title {
  font-size: 15px; font-weight: 600; color: var(--neutral-800); margin-bottom: 16px;
}
.reasoning-chain__steps { display: flex; flex-direction: column; }

.reasoning-step {
  display: flex; gap: 12px; align-items: flex-start; position: relative;
  animation: step-in 400ms ease-out both;
}
.reasoning-step__index {
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: #fff; flex-shrink: 0; z-index: 1;
}
.reasoning-step__index--ontology { background: var(--semantic-600); }
.reasoning-step__index--ml { background: var(--tier2-primary); }
.reasoning-step__index--rule { background: var(--kinetic-600); }
.reasoning-step__index--output { background: var(--dynamic-600); }

.reasoning-step__body {
  flex: 1; padding: 12px 16px; border-radius: var(--radius-lg);
  background: var(--neutral-50); border: 1px solid var(--neutral-200); margin-bottom: 12px;
}
.reasoning-step__type {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.3px; margin-bottom: 4px;
}
.reasoning-step__type--ontology { color: var(--semantic-600); }
.reasoning-step__type--ml { color: var(--tier2-primary); }
.reasoning-step__type--rule { color: var(--kinetic-600); }
.reasoning-step__type--output { color: var(--dynamic-600); }

.reasoning-step__source {
  font-family: var(--font-mono); font-size: 11px; color: var(--neutral-600);
  background: var(--neutral-100); padding: 2px 6px; border-radius: 3px;
  display: inline-block; margin-top: 4px;
}
.reasoning-step__result { font-size: 12px; color: var(--neutral-700); margin-top: 4px; }

.reasoning-chain__connector {
  position: absolute; left: 11px; top: 24px; bottom: -12px;
  width: 2px; border-left: 2px dashed var(--neutral-300);
}

@keyframes step-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
