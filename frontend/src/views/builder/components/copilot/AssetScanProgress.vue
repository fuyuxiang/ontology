<template>
  <div class="scan-process">
    <div class="scan-process__title">🔎 资产扫描中...</div>
    <div class="scan-process__list">
      <div
        v-for="(s, idx) in SCAN_STEPS"
        :key="s.key"
        class="scan-step"
        :class="{
          'scan-step--active': idx === activeStep,
          'scan-step--done': idx < activeStep,
        }"
      >
        <div class="scan-step__dot">
          <svg v-if="idx < activeStep" width="10" height="10" viewBox="0 0 10 10">
            <path d="M2 5l2 2 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
        </div>
        <div class="scan-step__main">
          <div class="scan-step__label">{{ s.label }}</div>
          <div class="scan-step__desc">{{ s.description }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { SCAN_STEPS } from '../../../../data/builderPresets'
defineProps<{ activeStep: number }>()
</script>

<style scoped>
.scan-process {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.05), rgba(99, 102, 241, 0.05));
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 14px;
}
.scan-process__title {
  font-size: 13px; font-weight: 600; color: #1e293b;
  margin-bottom: 10px;
}
.scan-process__list { display: grid; gap: 8px; }
.scan-step {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  transition: all 200ms ease;
}
.scan-step--active {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.04);
  box-shadow: 0 4px 12px -4px rgba(99, 102, 241, 0.2);
}
.scan-step--done { border-color: #10b981; background: rgba(16, 185, 129, 0.04); }
.scan-step__dot {
  width: 18px; height: 18px; border-radius: 50%;
  background: #f1f5f9; color: #fff;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 1px;
}
.scan-step--active .scan-step__dot {
  background: #6366f1;
  animation: scanPulse 1.5s ease-in-out infinite;
}
.scan-step--done .scan-step__dot { background: #10b981; }
@keyframes scanPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
  50% { box-shadow: 0 0 0 6px rgba(99, 102, 241, 0); }
}
.scan-step__label { font-size: 12px; font-weight: 600; color: #1e293b; line-height: 1.5; }
.scan-step__desc { font-size: 11px; color: #94a3b8; line-height: 1.5; }
</style>
