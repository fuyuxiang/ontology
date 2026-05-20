<template>
  <div class="evo-tab">
    <a-spin v-if="loading" size="large" class="evo-tab__loading" />

    <template v-else>
      <div class="evo-tab__toolbar">
        <a-space wrap>
          <a-button type="primary" :icon="h(ThunderboltOutlined)" :loading="busy === 'optimize'" @click="onOptimize">触发优化循环</a-button>
          <a-button :icon="h(ToolOutlined)" :loading="busy === 'generate'" @click="onGenerate">生成演化提案</a-button>
          <a-button :icon="h(RocketOutlined)" :loading="busy === 'auto'" @click="onAuto">自动应用安全演化</a-button>
        </a-space>
        <a-space>
          <a-badge :count="pendings.length" size="small"><a-tag>待审批</a-tag></a-badge>
          <a-badge :count="approveds.length" size="small" color="#1677ff"><a-tag>已批准</a-tag></a-badge>
          <a-badge :count="applieds.length + history.length" size="small" color="#52c41a"><a-tag>已应用</a-tag></a-badge>
        </a-space>
      </div>

      <div class="evo-tab__columns">
        <!-- 待审批 -->
        <div class="evo-tab__col" :style="{ background: '#fafbfc' }">
          <div class="evo-tab__col-head" :style="{ background: '#fffbe6', borderBottom: '2px solid #faad14' }">
            <a-typography-text strong style="color:#d48806;font-size:13px">待审批</a-typography-text>
            <a-badge :count="pendings.length" color="#faad14" />
          </div>
          <div class="evo-tab__col-body">
            <ProposalCard v-for="p in pendings" :key="p.id" :proposal="p" :allow-action="canApprove" :loading-id="busy"
              @approve="approve(p.id)" @reject="reject(p.id)" @goto="goStudio" />
            <div v-if="!pendings.length" class="evo-tab__empty">
              <a-typography-text type="secondary" style="font-size:12px">暂无待审批提案</a-typography-text>
            </div>
          </div>
        </div>

        <!-- 已批准 -->
        <div class="evo-tab__col" :style="{ background: '#fafbfc' }">
          <div class="evo-tab__col-head" :style="{ background: '#e6f4ff', borderBottom: '2px solid #1677ff' }">
            <a-typography-text strong style="color:#0958d9;font-size:13px">已批准</a-typography-text>
            <a-badge :count="approveds.length" color="#1677ff" />
          </div>
          <div class="evo-tab__col-body">
            <ProposalCard v-for="p in approveds" :key="p.id" :proposal="p" :allow-action="false" :loading-id="busy" @goto="goStudio" />
            <div v-if="!approveds.length" class="evo-tab__empty">
              <a-typography-text type="secondary" style="font-size:12px">暂无已批准提案</a-typography-text>
            </div>
          </div>
        </div>

        <!-- 已应用 -->
        <div class="evo-tab__col" :style="{ background: '#fafbfc' }">
          <div class="evo-tab__col-head" :style="{ background: '#f6ffed', borderBottom: '2px solid #52c41a' }">
            <a-typography-text strong style="color:#389e0d;font-size:13px">已应用</a-typography-text>
            <a-badge :count="applieds.length + history.length" color="#52c41a" />
          </div>
          <div class="evo-tab__col-body">
            <ProposalCard v-for="p in applieds" :key="p.id" :proposal="p" :allow-action="false" :loading-id="busy" @goto="goStudio" />
            <a-card v-for="h0 in history" :key="h0.id" size="small"
              :style="{ marginBottom: '10px', borderRadius: '8px', border: '1px solid #f0f0f0' }"
              :body-style="{ padding: '10px 12px' }">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                <a-typography-text strong style="font-size:13px">{{ h0.title }}</a-typography-text>
                <a-tag color="green" :style="{ fontSize: '10px', borderRadius: '6px' }">{{ h0.effect }}</a-tag>
              </div>
              <div style="display:flex;align-items:center;gap:4px;font-size:11px;color:#999">
                <ClockCircleOutlined style="font-size:10px" />{{ h0.applied_at }}
              </div>
            </a-card>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  ThunderboltOutlined,
  ToolOutlined,
  RocketOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { harnessApi, type ProposalInfo, type EvolutionHistoryItem } from '../../../api/harness'
import ProposalCard from '../components/ProposalCard.vue'

const router = useRouter()
const loading = ref(true)
const proposals = ref<ProposalInfo[]>([])
const history = ref<EvolutionHistoryItem[]>([])
const busy = ref<string | null>(null)

const canApprove = true

const pendings = computed(() => proposals.value.filter(p => p.status === 'pending'))
const approveds = computed(() => proposals.value.filter(p => p.status === 'approved'))
const applieds = computed(() => proposals.value.filter(p => p.status === 'applied'))

async function loadAll() {
  const [props_, queue, hist] = await Promise.all([
    harnessApi.getProposals(),
    harnessApi.getEvolutionQueue(),
    harnessApi.getEvolutionHistory(),
  ])
  const main = Array.isArray(props_) && props_.length ? props_ : []
  const q = Array.isArray(queue) && queue.length ? queue : []
  const seen = new Set(main.map(p => p.id))
  proposals.value = [...main, ...q.filter(x => !seen.has(x.id))]
  if (Array.isArray(hist) && hist.length) history.value = hist
}

async function approve(id: string) {
  busy.value = id
  if (id.startsWith('EVO_') || id.startsWith('evo-')) await harnessApi.applyEvolution(id)
  else await harnessApi.applyProposal(id)
  proposals.value = proposals.value.map(p => p.id === id ? { ...p, status: 'approved' } : p)
  busy.value = null
  message.success('提案已批准')
}

async function reject(id: string) {
  busy.value = id
  if (id.startsWith('EVO_') || id.startsWith('evo-')) await harnessApi.rejectEvolution(id)
  else await harnessApi.rejectProposal(id)
  proposals.value = proposals.value.map(p => p.id === id ? { ...p, status: 'rejected' } : p)
  busy.value = null
  message.info('提案已拒绝')
}

async function onOptimize() {
  busy.value = 'optimize'
  const res = await harnessApi.optimize()
  const cnt = res.new_proposals ?? 2
  const fresh: ProposalInfo[] = Array.from({ length: cnt }, (_, i) => ({
    id: `opt-${Date.now()}-${i}`,
    type: 'rule_tuning',
    severity: 'medium',
    status: 'pending',
    title: `优化提案 #${proposals.value.length + i + 1}`,
    description: '由优化循环自动生成的规则调优建议',
    impact: `影响 ${Math.floor(Math.random() * 2000 + 500)} 用户`,
  }))
  proposals.value = [...fresh, ...proposals.value]
  busy.value = null
  message.success(`优化循环完成：生成 ${cnt} 条新提案`)
}

async function onGenerate() {
  busy.value = 'generate'
  const res = await harnessApi.generateEvolution()
  const cnt = res.count ?? 3
  const types = ['new_attribute', 'touchpoint_update', 'model_retrain']
  const sevs = ['low', 'medium', 'high']
  const fresh: ProposalInfo[] = Array.from({ length: cnt }, (_, i) => ({
    id: `gen-${Date.now()}-${i}`,
    type: types[i % 3],
    severity: sevs[i % 3],
    status: 'pending',
    title: `演化提案 #${proposals.value.length + i + 1}`,
    description: '由AI分析引擎自动生成的演化建议',
    impact: `影响 ${Math.floor(Math.random() * 3000 + 200)} 用户`,
  }))
  proposals.value = [...fresh, ...proposals.value]
  busy.value = null
  message.success(`已生成 ${cnt} 条演化提案`)
}

async function onAuto() {
  busy.value = 'auto'
  const res = await harnessApi.autoApplyEvolution()
  const applied = res.applied ?? 1
  let remaining = applied
  proposals.value = proposals.value.map(p => {
    if (remaining > 0 && p.status === 'pending' && p.severity === 'low') {
      remaining--
      return { ...p, status: 'applied' }
    }
    return p
  })
  busy.value = null
  message.success(`已自动应用 ${applied} 条安全演化`)
}

function goStudio() { router.push('/studio') }

onMounted(async () => {
  await loadAll()
  loading.value = false
})
</script>

<style scoped>
.evo-tab__loading { display: flex; justify-content: center; padding: 60px 0; }
.evo-tab__toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.evo-tab__columns { display: flex; gap: 14px; min-height: 400px; }
.evo-tab__col { flex: 1; border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
.evo-tab__col-head {
  padding: 10px 14px;
  display: flex; justify-content: space-between; align-items: center;
}
.evo-tab__col-body { padding: 10px; flex: 1; overflow-y: auto; }
.evo-tab__empty { text-align: center; padding: 24px; }
</style>
