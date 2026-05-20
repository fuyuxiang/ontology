<template>
  <div class="exp-tab">
    <a-spin v-if="loading" size="large" class="exp-tab__loading" />

    <template v-else>
      <!-- 顶部统计 4 张 -->
      <a-row :gutter="[16, 16]" style="margin-bottom:16px">
        <a-col v-for="s in stats" :key="s.label" :xs="6">
          <a-card size="small" :body-style="{ padding: '12px 16px', textAlign: 'center' }"
            :style="{ borderRadius: '10px', borderTop: `3px solid ${s.color}` }">
            <div style="font-size:11px;color:#999">{{ s.label }}</div>
            <div :style="{ fontSize: '28px', fontWeight: 700, color: s.color, lineHeight: 1.2 }">{{ s.value }}</div>
          </a-card>
        </a-col>
      </a-row>

      <a-button type="primary" :icon="h(PlusOutlined)" @click="showCreate = true" style="margin-bottom:16px">
        创建实验
      </a-button>

      <a-row :gutter="[12, 12]">
        <a-col v-for="exp in experiments" :key="exp.id" :xs="24" :md="12">
          <a-card size="small" hoverable :style="{ borderRadius: '10px', borderLeft: `4px solid ${statusOf(exp.status).color}` }">
            <div class="exp-tab__head">
              <a-space>
                <ThunderboltOutlined :style="{ color: statusOf(exp.status).color }" />
                <a-typography-text strong style="font-size:13px">{{ exp.name }}</a-typography-text>
              </a-space>
              <a-tag :color="statusOf(exp.status).color" :style="{ borderRadius: '10px', fontSize: '11px' }">
                {{ statusOf(exp.status).text }}
              </a-tag>
            </div>

            <div class="exp-tab__body">
              <div style="flex-shrink:0">
                <div style="font-size:10px;color:#999;margin-bottom:2px">
                  <span class="exp-tab__sq" style="background:#8c8c8c;opacity:0.25"></span>对照组
                </div>
                <div style="font-size:10px;color:#999">
                  <span class="exp-tab__sq" :style="{ background: exp.p_value < 0.05 ? '#52c41a' : '#1677ff', opacity: 0.35 }"></span>实验组
                </div>
              </div>
              <ABStatBar :control="exp.control_rate" :treatment="exp.treatment_rate" :p-value="exp.p_value" />
            </div>

            <div class="exp-tab__metrics">
              <div :style="{ padding: '4px 10px', background: liftOf(exp) > 0 ? '#f6ffed' : '#fff2f0', borderRadius: '6px' }">
                <a-typography-text :style="{ fontSize: '18px', fontWeight: 700, color: liftOf(exp) > 0 ? '#52c41a' : '#ff4d4f' }">
                  {{ liftOf(exp) > 0 ? '+' : '' }}{{ liftOf(exp).toFixed(1) }}%
                </a-typography-text>
                <a-typography-text type="secondary" style="font-size:11px;margin-left:4px">提升</a-typography-text>
              </div>
              <div :style="{ padding: '4px 10px', background: exp.p_value < 0.05 ? '#f6ffed' : '#fafafa', borderRadius: '6px' }">
                <a-typography-text :style="{ fontSize: '13px', fontWeight: 600, color: exp.p_value < 0.05 ? '#52c41a' : '#999' }">
                  p = {{ exp.p_value.toFixed(3) }}
                </a-typography-text>
                <a-tag v-if="exp.p_value < 0.05" color="green" :style="{ marginLeft: '6px', fontSize: '10px' }">显著</a-tag>
              </div>
            </div>

            <div style="margin-bottom:8px">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <a-typography-text type="secondary" style="font-size:11px">样本进度</a-typography-text>
                <a-typography-text type="secondary" style="font-size:11px">
                  {{ (exp.sample_size ?? 0).toLocaleString() }} / {{ (exp.target_sample ?? 1000).toLocaleString() }}
                </a-typography-text>
              </div>
              <a-progress :percent="progressOf(exp)" size="small" :stroke-color="statusOf(exp.status).color" :show-info="false" />
            </div>

            <div class="exp-tab__actions">
              <a-button v-if="exp.status === 'running'" size="small" :icon="h(PauseCircleOutlined)" @click="stop(exp.id)">停止</a-button>
              <a-button v-if="exp.status === 'significant' || (exp.status === 'completed' && exp.p_value < 0.05)"
                type="primary" size="small" :icon="h(CheckCircleOutlined)" @click="applyWin(exp.id)">
                应用胜出方案
              </a-button>
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 创建实验对话框 -->
      <a-modal v-model:open="showCreate" title="创建 A/B 实验" :confirm-loading="creating" ok-text="创建" cancel-text="取消" @ok="onCreate">
        <a-form :model="form" layout="vertical">
          <a-form-item label="实验名称" required>
            <a-input v-model:value="form.name" placeholder="例: 话术A vs 话术B" />
          </a-form-item>
          <a-form-item label="目标分群" required>
            <a-select v-model:value="form.segment" placeholder="选择分群">
              <a-select-option v-for="s in MOCK_SEGMENTS" :key="s.id" :value="s.id">{{ s.name }}</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="对照策略" required>
            <a-input v-model:value="form.control_strategy" placeholder="当前生产策略" />
          </a-form-item>
          <a-form-item label="实验策略" required>
            <a-input v-model:value="form.treatment_strategy" placeholder="新策略方案" />
          </a-form-item>
          <a-form-item label="流量分配 (实验组占比)">
            <a-slider v-model:value="form.traffic_split" :min="10" :max="90" :marks="{ 10: '10%', 50: '50/50', 90: '90%' }" />
          </a-form-item>
          <a-form-item label="最小样本量">
            <a-input-number v-model:value="form.min_sample" :min="100" :max="10000" style="width:100%" />
          </a-form-item>
        </a-form>
      </a-modal>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import {
  ThunderboltOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  SwapOutlined,
  PauseCircleOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { harnessApi, type ExperimentInfo } from '../../../api/harness'
import ABStatBar from '../components/ABStatBar.vue'

const MOCK_SEGMENTS = [
  { id: 'SEG_001', name: '高价值即将到期' },
  { id: 'SEG_002', name: '中价值流失风险' },
  { id: 'SEG_003', name: '低价值稳定' },
  { id: 'SEG_004', name: '高价值忠诚' },
  { id: 'SEG_005', name: '网络迁转潜力' },
  { id: 'SEG_006', name: '投诉风险群体' },
  { id: 'SEG_007', name: '一次性到期' },
]

const loading = ref(true)
const experiments = ref<ExperimentInfo[]>([])
const showCreate = ref(false)
const creating = ref(false)
const form = ref({
  name: '',
  segment: '',
  control_strategy: '',
  treatment_strategy: '',
  traffic_split: 50,
  min_sample: 1000,
})

const STATUS_MAP: Record<string, { color: string; text: string; bg: string }> = {
  running: { color: '#1677ff', text: '进行中', bg: '#e6f4ff' },
  completed: { color: '#8c8c8c', text: '已完成', bg: '#fafafa' },
  significant: { color: '#52c41a', text: '显著', bg: '#f6ffed' },
}

function statusOf(s: string) { return STATUS_MAP[s] || STATUS_MAP.completed }
function liftOf(e: ExperimentInfo) { return e.control_rate > 0 ? (e.treatment_rate - e.control_rate) / e.control_rate * 100 : 0 }
function progressOf(e: ExperimentInfo) { return Math.round((e.sample_size ?? 0) / (e.target_sample || 1000) * 100) }

const stats = computed(() => [
  { label: '进行中', value: experiments.value.filter(e => e.status === 'running').length, color: '#1677ff', icon: ThunderboltOutlined },
  { label: '已完成', value: experiments.value.filter(e => e.status === 'completed').length, color: '#8c8c8c', icon: CheckCircleOutlined },
  { label: '显著', value: experiments.value.filter(e => e.status === 'significant').length, color: '#52c41a', icon: CheckCircleOutlined },
  { label: '不显著', value: experiments.value.filter(e => e.status === 'completed' && (e.p_value ?? 1) >= 0.05).length, color: '#faad14', icon: SwapOutlined },
])

async function loadAll() {
  const list = await harnessApi.getExperiments()
  if (Array.isArray(list) && list.length) {
    experiments.value = list.map(e => ({
      ...e,
      control_rate: (e.control_rate ?? 0) <= 1 ? (e.control_rate ?? 0) * 100 : e.control_rate ?? 0,
      treatment_rate: (e.treatment_rate ?? 0) <= 1 ? (e.treatment_rate ?? 0) * 100 : e.treatment_rate ?? 0,
    }))
  }
}

async function onCreate() {
  if (!form.value.name || !form.value.segment) { message.error('请填写实验名称和分群'); return }
  creating.value = true
  await harnessApi.createExperiment(form.value)
  creating.value = false
  showCreate.value = false
  message.success('实验已创建')
  experiments.value.push({
    id: `EXP_${Date.now()}`,
    name: form.value.name,
    status: 'running',
    control_rate: 0,
    treatment_rate: 0,
    p_value: 1,
    sample_size: 0,
    target_sample: form.value.min_sample || 1000,
    segment: form.value.segment,
  })
  form.value = { name: '', segment: '', control_strategy: '', treatment_strategy: '', traffic_split: 50, min_sample: 1000 }
}

async function stop(id: string) {
  await harnessApi.stopExperiment(id)
  experiments.value = experiments.value.map(e => e.id === id ? { ...e, status: 'completed' } : e)
  message.success('实验已停止')
}

async function applyWin(id: string) {
  await harnessApi.applyEvolution(id)
  experiments.value = experiments.value.map(e => e.id === id ? { ...e, status: 'completed' } : e)
  message.success('胜出方案已应用到生产环境')
}

onMounted(async () => {
  await loadAll()
  loading.value = false
})
</script>

<style scoped>
.exp-tab__loading { display: flex; justify-content: center; padding: 60px 0; }
.exp-tab__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.exp-tab__body { display: flex; align-items: center; gap: 12px; }
.exp-tab__sq { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; }
.exp-tab__metrics { display: flex; align-items: center; gap: 16px; margin: 10px 0 6px; }
.exp-tab__actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
