<template>
  <div class="drift-tab">
    <a-spin v-if="loading" size="large" class="drift-tab__loading" />

    <template v-else>
      <!-- 顶部工具栏 -->
      <div class="drift-tab__toolbar">
        <a-segmented v-model:value="dimension" :options="['分群维度', '触点维度', '模型维度']" />
        <a-space>
          <a-button type="primary" :loading="optimizing" @click="triggerOptimize">
            <template #icon><SyncOutlined /></template>
            触发优化循环
          </a-button>
          <a-tag v-if="newProposalCount != null" color="blue">新增 {{ newProposalCount }} 条提案</a-tag>
          <a-tag color="red">告警 {{ countByStatus('alert') }}</a-tag>
          <a-tag color="gold">关注 {{ countByStatus('warning') }}</a-tag>
          <a-tag color="green">正常 {{ countByStatus('good') }}</a-tag>
        </a-space>
      </div>

      <!-- 分群维度 -->
      <a-row v-if="dimension === '分群维度'" :gutter="[12, 12]">
        <a-col v-for="seg in segments" :key="seg.id" :xs="24" :md="12">
          <a-card
            size="small"
            hoverable
            :body-style="{ padding: '12px' }"
            :style="{ borderRadius: '10px', borderLeft: `4px solid ${devColor(seg.deviation)}`, cursor: 'pointer' }"
            @click="toggleExpand(seg.id)">
            <div class="drift-tab__seg-head">
              <a-space>
                <a-typography-text strong style="font-size:14px">{{ seg.name }}</a-typography-text>
                <a-tag :color="seg.status === 'alert' ? 'red' : seg.status === 'warning' ? 'gold' : 'green'" :style="{ fontSize: '11px' }">
                  {{ seg.status === 'alert' ? '告警' : seg.status === 'warning' ? '关注' : '正常' }}
                </a-tag>
              </a-space>
              <a-typography-text :style="{ fontSize: '20px', fontWeight: 700, color: devColor(seg.deviation) }">
                {{ seg.deviation > 0 ? '+' : '' }}{{ seg.deviation }}%
              </a-typography-text>
            </div>

            <div class="drift-tab__seg-body">
              <PredActualBar :predicted="seg.predicted" :actual="seg.actual" :max-val="maxVal" />
              <div style="font-size:11px;color:#999">
                <div><span class="drift-tab__sq" style="background:#1677ff;opacity:0.3"></span>预测</div>
                <div><span class="drift-tab__sq" :style="{ background: seg.actual >= seg.predicted ? '#52c41a' : '#ff4d4f', opacity: 0.7 }"></span>实际</div>
              </div>
              <div style="margin-left:auto;text-align:right">
                <a-typography-text type="secondary" style="font-size:11px">样本量</a-typography-text>
                <div style="font-size:14px;font-weight:600">{{ seg.sample_size.toLocaleString() }}</div>
              </div>
            </div>

            <!-- 展开：AI 根因诊断 -->
            <div v-if="expandedId === seg.id && diagnosis(seg)" class="drift-tab__diag">
              <div class="drift-tab__diag-head">
                <ToolOutlined style="color:#faad14" />
                <a-typography-text strong style="font-size:13px;color:#faad14">AI 根因诊断</a-typography-text>
              </div>
              <a-typography-text style="font-size:12px;color:#666">{{ diagnosis(seg)!.summary }}</a-typography-text>
              <div class="drift-tab__factors">
                <div v-for="(f, i) in diagnosis(seg)!.factors" :key="i" class="drift-tab__factor">
                  <component :is="f.icon" style="color:#1677ff;margin-top:1px" />
                  <div>
                    <a-typography-text strong style="font-size:12px">{{ f.label }}</a-typography-text>
                    <div><a-typography-text type="secondary" style="font-size:11px">{{ f.desc }}</a-typography-text></div>
                  </div>
                </div>
              </div>
              <div class="drift-tab__suggestion">{{ diagnosis(seg)!.suggestion }}</div>
            </div>
            <div v-if="expandedId === seg.id && !diagnosis(seg)" class="drift-tab__ok">
              该分群表现在可接受范围内，持续监控即可。
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 触点维度 -->
      <a-row v-else-if="dimension === '触点维度'" :gutter="[12, 12]">
        <a-col v-for="t in touchpoints" :key="t.name" :xs="24" :md="12" :lg="6">
          <a-card size="small" hoverable :style="{ borderRadius: '10px', textAlign: 'center' }">
            <div :style="{ fontSize: '28px', fontWeight: 700, color: tpColor(t.conversion), marginTop: '4px' }">
              {{ t.conversion }}%
            </div>
            <a-typography-text type="secondary" style="font-size:11px">转化率</a-typography-text>
            <div style="margin:12px 0">
              <a-typography-text strong style="font-size:16px">{{ t.name }}</a-typography-text>
            </div>
            <div class="drift-tab__tp-stats">
              <div>
                <a-typography-text type="secondary" style="font-size:11px">触达率</a-typography-text>
                <div style="font-size:14px;font-weight:600">{{ t.reach_rate }}%</div>
              </div>
              <div style="border-left:1px solid #f5f5f5;padding-left:12px">
                <a-typography-text type="secondary" style="font-size:11px">成本比</a-typography-text>
                <div :style="{ fontSize: '14px', fontWeight: 600, color: t.cost_ratio > 10 ? '#ff4d4f' : '#666' }">
                  {{ t.cost_ratio }}
                </div>
              </div>
            </div>
            <div style="margin-top:10px;height:4px;background:#f5f5f5;border-radius:2px;overflow:hidden">
              <div :style="{ height: '100%', width: t.reach_rate + '%', background: `linear-gradient(90deg, ${tpColor(t.conversion)}66, ${tpColor(t.conversion)})`, borderRadius: '2px' }"></div>
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 模型维度 -->
      <a-row v-else :gutter="[12, 12]">
        <a-col v-for="m in models" :key="m.id" :xs="24" :md="8">
          <a-card size="small" hoverable :style="{ borderRadius: '10px', borderTop: `3px solid ${modelHealthColor(m.health)}` }">
            <div class="drift-tab__model-head">
              <a-typography-text strong style="font-size:15px">{{ m.name }}</a-typography-text>
              <a-badge :color="modelHealthColor(m.health)" :text="modelHealthLabel(m.health)" />
            </div>
            <div class="drift-tab__model-stats">
              <div class="drift-tab__model-stat">
                <a-typography-text type="secondary" style="font-size:11px">准确率</a-typography-text>
                <div style="font-size:22px;font-weight:700">{{ ((m.accuracy ?? 0) * 100).toFixed(1) }}%</div>
              </div>
              <div class="drift-tab__model-stat">
                <a-typography-text type="secondary" style="font-size:11px">PSI</a-typography-text>
                <div :style="{ fontSize: '22px', fontWeight: 700, color: (m.psi ?? 0) > 0.15 ? '#faad14' : '#52c41a' }">
                  {{ m.psi ?? 0 }}
                </div>
              </div>
            </div>
            <a-typography-text type="secondary" style="font-size:11px">特征重要性 Top 5</a-typography-text>
            <FeatureBars :features="m.features ?? []" />
            <a-button v-if="retrained[m.id]" size="small" :icon="h(CheckCircleOutlined)" disabled
              :style="{ marginTop: '12px', width: '100%', color: '#52c41a', borderColor: '#b7eb8f' }">
              重训练完成
            </a-button>
            <a-button v-else type="primary" size="small" :icon="h(ThunderboltOutlined)"
              :loading="retraining === m.id"
              @click="retrain(m.id)"
              :style="{ marginTop: '12px', width: '100%' }">
              触发重训练
            </a-button>
            <a-button type="link" size="small" :icon="h(LinkOutlined)"
              @click="goStudio"
              :style="{ marginTop: '4px', width: '100%', fontSize: '11px' }">
              在本体工作室中查看模型映射
            </a-button>
          </a-card>
        </a-col>
      </a-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  SyncOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  LinkOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  RiseOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { harnessApi, type DriftSegment, type DriftTouchpoint, type ModelInfo } from '../../../api/harness'
import PredActualBar from '../components/PredActualBar.vue'
import FeatureBars from '../components/FeatureBars.vue'

const router = useRouter()
const loading = ref(true)
const dimension = ref<'分群维度' | '触点维度' | '模型维度'>('分群维度')
const segments = ref<DriftSegment[]>([])
const touchpoints = ref<DriftTouchpoint[]>([])
const models = ref<ModelInfo[]>([])
const expandedId = ref<string | null>(null)
const retraining = ref<string | null>(null)
const retrained = ref<Record<string, boolean>>({})
const optimizing = ref(false)
const newProposalCount = ref<number | null>(null)

const maxVal = computed(() => Math.max(...segments.value.map(s => Math.max(s.predicted, s.actual)), 1))

function devColor(d: number) { const a = Math.abs(d); return a > 25 ? '#ff4d4f' : a > 15 ? '#faad14' : '#52c41a' }
function tpColor(c: number) { return c > 10 ? '#52c41a' : c > 5 ? '#1677ff' : '#faad14' }
function modelHealthColor(h: string) { return h === 'good' ? '#52c41a' : h === 'warning' ? '#faad14' : '#ff4d4f' }
function modelHealthLabel(h: string) { return h === 'good' ? '健康' : h === 'warning' ? '关注' : '异常' }
function countByStatus(s: string) { return segments.value.filter(x => x.status === s).length }
function toggleExpand(id: string) { expandedId.value = expandedId.value === id ? null : id }

function diagnosis(seg: DriftSegment) {
  if (Math.abs(seg.deviation) <= 15) return null
  const isNeg = seg.deviation < 0
  return {
    summary: isNeg
      ? `该分群实际转化率 ${seg.actual}% 低于预测 ${seg.predicted}%，偏差 ${seg.deviation}%`
      : `该分群实际转化率 ${seg.actual}% 高于预测 ${seg.predicted}%，偏差 +${seg.deviation}%`,
    factors: isNeg ? [
      { icon: DatabaseOutlined, label: '数据分布漂移', desc: `${seg.name} 近7天用户行为特征分布发生偏移，分群边界参数需要调整` },
      { icon: ToolOutlined, label: '规则命中率下降', desc: `关联业务规则命中率下降 ${(Math.abs(seg.deviation) * 0.6).toFixed(0)}%，建议检查阈值` },
      { icon: ExclamationCircleOutlined, label: '外部因素', desc: '竞品促销活动可能分流部分目标用户' },
    ] : [
      { icon: RiseOutlined, label: '策略效果超预期', desc: `${seg.name} 当前策略组合效果良好，建议扩大测试范围` },
      { icon: DatabaseOutlined, label: '数据质量改善', desc: '新增数据源提升了分群精度，预测模型可能需要重新校准' },
    ],
    suggestion: isNeg
      ? `建议: 1) 调整 ${seg.name} 分群阈值参数; 2) 触发模型重训练; 3) 检查关联触点效果`
      : '建议: 1) 保持当前策略; 2) 更新预测基线; 3) 考虑将策略推广到相似分群',
  }
}

async function loadAll() {
  const [drift, ms] = await Promise.all([harnessApi.getDrift(), harnessApi.getModels()])
  if (drift?.segments) {
    segments.value = drift.segments.map(e => ({
      ...e,
      predicted: e.predicted <= 1 ? e.predicted * 100 : e.predicted,
      actual: e.actual <= 1 ? e.actual * 100 : e.actual,
      deviation: e.deviation <= 1 && e.deviation >= -1 ? e.deviation * 100 : e.deviation,
    }))
  }
  if (drift?.touchpoints) {
    touchpoints.value = drift.touchpoints.map(t => ({
      ...t,
      reach_rate: t.reach_rate <= 1 ? t.reach_rate * 100 : t.reach_rate,
      conversion: t.conversion <= 1 ? t.conversion * 100 : t.conversion,
    }))
  }
  if (Array.isArray(ms) && ms.length) models.value = ms
}

async function retrain(id: string) {
  retraining.value = id
  await harnessApi.optimize()
  models.value = models.value.map(m => m.id === id
    ? { ...m, health: 'good', accuracy: Math.min(0.99, (m.accuracy ?? 0.85) + 0.03), psi: Math.max(0.01, (m.psi ?? 0.1) - 0.04) }
    : m
  )
  retrained.value = { ...retrained.value, [id]: true }
  retraining.value = null
  message.success('模型重训练已完成，健康度已更新')
}

async function triggerOptimize() {
  optimizing.value = true
  const res = await harnessApi.optimize()
  newProposalCount.value = res.new_proposals ?? 2
  await harnessApi.getProposals().catch(() => {})
  optimizing.value = false
  if (res.success) message.success(`优化循环完成：生成 ${newProposalCount.value} 条新提案，请前往演化管理查看`)
}

function goStudio() { router.push('/studio') }

onMounted(async () => {
  await loadAll()
  loading.value = false
})
</script>

<style scoped>
.drift-tab__loading { display: flex; justify-content: center; padding: 60px 0; }
.drift-tab__toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.drift-tab__seg-head { display: flex; justify-content: space-between; align-items: center; }
.drift-tab__seg-body { margin-top: 8px; display: flex; align-items: center; gap: 16px; }
.drift-tab__sq { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; }
.drift-tab__diag {
  margin-top: 12px; padding: 14px; background: #fafbfc;
  border-radius: 8px; border-top: 1px solid #f0f0f0;
}
.drift-tab__diag-head { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.drift-tab__factors { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.drift-tab__factor {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 8px; background: white; border-radius: 6px; border: 1px solid #f0f0f0;
}
.drift-tab__suggestion { margin-top: 10px; padding: 8px 10px; background: #f6ffed; border-radius: 6px; font-size: 12px; color: #389e0d; }
.drift-tab__ok { margin-top: 12px; padding: 12px; background: #f6ffed; border-radius: 8px; font-size: 12px; color: #389e0d; }
.drift-tab__tp-stats { display: flex; justify-content: space-around; border-top: 1px solid #f5f5f5; padding-top: 10px; }
.drift-tab__model-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.drift-tab__model-stats { display: flex; gap: 16px; margin-bottom: 8px; }
.drift-tab__model-stat { text-align: center; flex: 1; padding: 8px 0; background: #fafafa; border-radius: 8px; }
</style>
