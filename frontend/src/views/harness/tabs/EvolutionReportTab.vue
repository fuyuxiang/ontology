<template>
  <div class="report-tab">
    <a-spin v-if="loading" size="large" class="report-tab__loading" />

    <template v-else>
      <!-- 时间线说明条 -->
      <div class="report-tab__timeline-card">
        <div class="report-tab__timeline-head">
          <BranchesOutlined style="color:#0891B2" />
          <span style="font-weight:700;font-size:14px">本体进化时间线</span>
          <a-tag color="cyan">自学习闭环</a-tag>
        </div>
        <a-timeline mode="left" :items="timelineItems" />
      </div>

      <!-- 4 张统计卡 -->
      <a-row :gutter="[16, 16]">
        <a-col v-for="(s, i) in stats" :key="i" :xs="12" :lg="6">
          <a-card size="small" :body-style="{ padding: '14px 16px' }"
            :style="{ borderRadius: '10px', borderTop: `3px solid ${s.color}` }">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
              <span :style="{ color: s.color }"><component :is="s.icon" /></span>
              <a-typography-text type="secondary" style="font-size:12px">{{ s.label }}</a-typography-text>
            </div>
            <div>
              <span :style="{ fontSize: '28px', fontWeight: 700, color: s.color }">{{ s.value }}</span>
              <span style="font-size:12px;color:#999;margin-left:4px">{{ s.suffix }}</span>
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 转化率趋势 + 本体版本时间线 -->
      <a-row :gutter="[16, 16]" style="margin-top:16px;display:flex;align-items:stretch">
        <a-col :xs="24" :lg="14" style="display:flex">
          <a-card class="report-tab__trend-card">
            <template #title><RiseOutlined style="color:#52c41a" /> 转化率趋势</template>
            <div class="report-tab__trend-summary">
              <div style="text-align:center">
                <a-typography-text type="secondary" style="font-size:11px">优化前</a-typography-text>
                <div style="font-size:28px;font-weight:700;color:#8c8c8c">{{ report.conversion_before }}%</div>
              </div>
              <div style="display:flex;flex-direction:column;align-items:center">
                <RiseOutlined style="font-size:24px;color:#52c41a" />
                <a-tag color="green" :style="{ marginTop: '4px', fontSize: '13px', padding: '2px 10px', fontWeight: 700 }">
                  +{{ report.conversion_lift }}%
                </a-tag>
              </div>
              <div style="text-align:center">
                <a-typography-text type="secondary" style="font-size:11px">优化后</a-typography-text>
                <div style="font-size:28px;font-weight:700;color:#52c41a">{{ report.conversion_after }}%</div>
              </div>
            </div>
            <ConversionTrend :before="report.conversion_before" :after="report.conversion_after" :lift="report.conversion_lift" />
          </a-card>
        </a-col>

        <a-col :xs="24" :lg="10" style="display:flex">
          <a-card class="report-tab__version-card">
            <template #title><ClockCircleOutlined /> 本体版本时间线</template>
            <VersionTimeline :timeline="report.timeline ?? []" />
          </a-card>
        </a-col>
      </a-row>

      <!-- AI 总结 -->
      <a-card class="report-tab__ai-card" :body-style="{ padding: '16px 20px' }">
        <div style="display:flex;align-items:flex-start;gap:12px">
          <div class="report-tab__ai-avatar">
            <RobotOutlined style="font-size:18px;color:#1677ff" />
          </div>
          <div>
            <a-typography-text strong style="font-size:13px;color:#1677ff">AI 本周总结</a-typography-text>
            <a-typography-paragraph :style="{ fontSize: '13px', margin: '4px 0 0', color: '#333', lineHeight: 1.7 }">
              {{ report.ai_summary }}
            </a-typography-paragraph>
          </div>
        </div>
      </a-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import {
  BranchesOutlined,
  RiseOutlined,
  RobotOutlined,
  ClockCircleOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  DollarOutlined,
} from '@ant-design/icons-vue'
import { harnessApi, type ReportInfo } from '../../../api/harness'
import ConversionTrend from '../components/ConversionTrend.vue'
import VersionTimeline from '../components/VersionTimeline.vue'

const loading = ref(true)
const report = ref<ReportInfo>({
  new_attributes: 0, rule_tunings: 0, model_retrains: 0,
  conversion_before: 0, conversion_after: 0, conversion_lift: 0,
  roi_monthly: 0, ai_summary: '', timeline: [],
})

const stats = computed(() => [
  { label: '新增属性', value: report.value.new_attributes ?? 0, suffix: '个', icon: ToolOutlined, color: '#1677ff' },
  { label: '规则调优', value: report.value.rule_tunings ?? 0, suffix: '条', icon: ThunderboltOutlined, color: '#fa8c16' },
  { label: '模型重训', value: report.value.model_retrains ?? 0, suffix: '次', icon: RobotOutlined, color: '#722ed1' },
  { label: 'ROI 影响', value: ((report.value.roi_monthly ?? 0) / 10000).toFixed(1), suffix: '万/月', icon: DollarOutlined, color: '#52c41a' },
])

const timelineItems = computed(() => [
  { color: '#EF4444', label: '3月15日', children: h('span', null, [h('a-tag', { color: 'red' }, () => '漂移检测'), ' 流失预测模型准确率下降至82.3%，低于85%阈值']) },
  { color: '#F59E0B', label: '3月16日', children: h('span', null, [h('a-tag', { color: 'orange' }, () => '演化提案'), ' 系统自动生成：调整 BR_SEG_002 阈值从 0.6 到 0.5']) },
  { color: '#3B82F6', label: '3月17日', children: h('span', null, [h('a-tag', { color: 'blue' }, () => '人工审批'), ' 运营经理审批通过，确认规则调整合理']) },
  { color: '#10B981', label: '3月18日', children: h('span', null, [h('a-tag', { color: 'green' }, () => '写回本体'), ' 规则 BR_SEG_002 已更新，本体版本升级至 v3.1.0']) },
  { color: '#8B5CF6', label: '3月25日', children: h('span', null, [h('a-tag', { color: 'purple' }, () => '效果验证'), ' 提速潜力户转化率从 4.2% 提升至 6.3%，验证有效']) },
])

async function loadAll() {
  const [r, hist] = await Promise.all([harnessApi.getReport(), harnessApi.getEvolutionHistory()])
  let merged = r.ai_summary ? r : report.value
  // 用历史记录补全统计
  const stats0 = (Array.isArray(hist) && hist.length ? hist : []).reduce((acc: any, item: any) => {
    const t = (item.title || '').toLowerCase()
    if (t.includes('属性') || t.includes('attribute')) acc.new_attributes++
    else if (t.includes('模型') || t.includes('model')) acc.model_retrains++
    else acc.rule_tunings++
    return acc
  }, { new_attributes: 0, rule_tunings: 0, model_retrains: 0 })
  if (stats0.new_attributes + stats0.rule_tunings + stats0.model_retrains > 0) {
    merged = { ...merged, ...stats0 }
  }
  report.value = merged
}

onMounted(async () => {
  await loadAll()
  loading.value = false
})
</script>

<style scoped>
.report-tab__loading { display: flex; justify-content: center; padding: 60px 0; }
.report-tab__timeline-card {
  margin-bottom: 16px; padding: 16px; background: #fff;
  border-radius: 12px; border: 1px solid #e2e8f0;
}
.report-tab__timeline-head {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
}
.report-tab__trend-card { border-radius: 10px; width: 100%; }
.report-tab__version-card { border-radius: 10px; width: 100%; }
.report-tab__trend-summary {
  display: flex; align-items: center; justify-content: center; gap: 32px; padding: 8px 0;
}
.report-tab__ai-card {
  margin-top: 16px;
  border-radius: 10px;
  background: linear-gradient(135deg, #f6ffed 0%, #e6f4ff 100%);
}
.report-tab__ai-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  background: white; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
</style>
