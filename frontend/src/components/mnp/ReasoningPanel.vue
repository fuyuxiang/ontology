<template>
  <div class="reasoning">
    <div class="reasoning__section">
      <div class="reasoning__title">推理链</div>
      <div class="reasoning__steps">
        <div v-for="(s, i) in signals" :key="i" class="reasoning__step">
          <div class="step__num">{{ i + 1 }}</div>
          <div class="step__body">
            <div class="step__type">{{ s.type }} <span class="step__weight">权重 {{ s.weight }}</span></div>
            <div class="step__detail">{{ s.detail }}</div>
            <div class="step__time">{{ s.time }}</div>
          </div>
        </div>
        <div class="reasoning__step reasoning__step--result">
          <div class="step__num step__num--result">∑</div>
          <div class="step__body">
            <div class="step__type">综合评分: {{ user.riskScore }}分 → {{ levelLabel }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="reasoning__section" v-if="actions.length > 0">
      <div class="reasoning__title">维挽动作</div>
      <div class="action-list">
        <div v-for="(a, i) in actions" :key="i" class="action-item">
          <div class="action-item__icon" :class="`action-icon--${a.status === '已完成' ? 'done' : 'pending'}`">
            <svg v-if="a.status === '已完成'" width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7l3 3 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <svg v-else width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="3" stroke="currentColor" stroke-width="1.5"/></svg>
          </div>
          <div class="action-item__body">
            <div class="action-item__name">{{ a.type }} <span class="action-item__status">{{ a.status }}</span></div>
            <div class="action-item__meta">
              {{ a.time }}
              <span v-if="a.effect"> · 效果: {{ a.effect }}</span>
              <span v-if="a.scoreAfter != null"> · 评分 {{ a.scoreBefore }} → {{ a.scoreAfter }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="reasoning__actions" v-if="user.mnpStatus === '预警中'">
      <button class="action-btn action-btn--primary">发送专属优惠</button>
      <button class="action-btn action-btn--secondary">派发回访</button>
      <button class="action-btn action-btn--secondary">套餐升级</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RiskUser, Signal, Action } from '../../views/scene/MnpWorkbench.vue'

const props = defineProps<{ user: RiskUser; signals: Signal[]; actions: Action[] }>()
const levelLabels: Record<string, string> = { high: '高风险', medium: '中风险', low: '低风险', safe: '安全' }
const levelLabel = computed(() => levelLabels[props.user.riskLevel])
</script>

<style scoped>
.reasoning { background: #fff; border-radius: 10px; border: 1px solid #e9ecef; padding: 16px; }
.reasoning__section { margin-bottom: 16px; }
.reasoning__section:last-child { margin-bottom: 0; }
.reasoning__title { font-size: 14px; font-weight: 600; color: #343a40; margin-bottom: 10px; }
.reasoning__steps { display: flex; flex-direction: column; gap: 2px; }
.reasoning__step { display: flex; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f8f9fa; }
.step__num { width: 24px; height: 24px; border-radius: 50%; background: #eef2ff; color: #4c6ef5; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.step__num--result { background: #fa5252; color: #fff; }
.reasoning__step--result { border-bottom: none; padding-top: 10px; }
.step__type { font-size: 13px; font-weight: 500; color: #343a40; }
.step__weight { font-size: 10px; color: #adb5bd; margin-left: 6px; }
.step__detail { font-size: 12px; color: #495057; margin-top: 2px; }
.step__time { font-size: 10px; color: #adb5bd; margin-top: 2px; }
.action-list { display: flex; flex-direction: column; gap: 6px; }
.action-item { display: flex; gap: 10px; align-items: flex-start; }
.action-item__icon { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.action-icon--done { background: #e6fcf5; color: #12b886; }
.action-icon--pending { background: #fff8e1; color: #f59f00; }
.action-item__name { font-size: 13px; font-weight: 500; color: #343a40; }
.action-item__status { font-size: 10px; color: #868e96; background: #f1f3f5; padding: 1px 6px; border-radius: 3px; margin-left: 4px; }
.action-item__meta { font-size: 11px; color: #868e96; margin-top: 2px; }
.reasoning__actions { display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #f1f3f5; }
.action-btn { padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; }
.action-btn--primary { background: #4c6ef5; color: #fff; }
.action-btn--primary:hover { background: #4263eb; }
.action-btn--secondary { background: #f1f3f5; color: #495057; }
.action-btn--secondary:hover { background: #e9ecef; }
</style>
