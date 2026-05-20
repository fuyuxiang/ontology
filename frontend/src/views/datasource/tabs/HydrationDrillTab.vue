<template>
  <div class="hd-tab">
    <!-- 列表视图 -->
    <div v-if="!activeReport" class="hd-list-view">
      <div class="hd-title-area">
        <div class="hd-title">水合演练历史</div>
        <div class="hd-subtitle">记录每次 T-box 水合验证的执行结果与评分 — 共 {{ records.length }} 条</div>
      </div>

      <div class="hd-toolbar">
        <a-segmented v-model:value="filter" :options="filterOptions" />
        <a-input v-model:value="search" placeholder="搜索场景、版本、时间…" allow-clear style="width: 280px" />
        <span style="flex:1"></span>
        <a-button type="primary" @click="startNewDrill">+ 新建水合演练</a-button>
      </div>

      <div class="hd-table-wrap">
        <table class="hd-table">
          <thead>
            <tr>
              <th>序号</th>
              <th>执行时间</th>
              <th>T-box 版本</th>
              <th>场景</th>
              <th>客户实例数</th>
              <th>验证结果</th>
              <th>综合评分</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filtered" :key="r.id" :class="{ 'row-fail': r.result === 'fail' }" @click="openReport(r)">
              <td class="hd-num">{{ r.id }}</td>
              <td class="hd-mono">{{ r.time }}</td>
              <td><span class="hd-version">{{ r.tboxVersion }}</span></td>
              <td>{{ r.scene }}</td>
              <td class="hd-bold">{{ r.customerCount }}</td>
              <td>
                <span v-if="r.result === 'pass'" class="hd-badge hd-badge--pass">✅ 通过</span>
                <span v-else class="hd-badge hd-badge--fail">❌ 失败</span>
              </td>
              <td>
                <span class="hd-score">
                  <span class="hd-dot" :class="scoreClass(r.score)"></span>{{ r.score }}
                </span>
              </td>
              <td @click.stop>
                <a-button type="primary" size="small" @click="openReport(r)">查看报告</a-button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="filtered.length === 0" class="hd-empty">暂无匹配记录</div>
      </div>
    </div>

    <!-- 报告视图 -->
    <div v-else class="hd-report-view">
      <div class="hd-report-bar">
        <a-button @click="activeReport = null">← 返回历史列表</a-button>
        <div class="hd-breadcrumb">数据工坊 / 水合演练 / <span>水合验证报告</span></div>
        <span style="flex:1"></span>
        <span class="hd-meta">报告编号 {{ reportNo(activeReport) }} · 生成时间 {{ activeReport.time }}</span>
        <a-button>⬇ 导出PDF</a-button>
        <a-button type="primary" style="background:#389e0d;border-color:#389e0d" @click="goPublish">🚀 发布本体 →</a-button>
      </div>

      <div class="hd-report-body">
        <!-- 状态横幅 -->
        <div class="hd-banner" :class="activeReport.result === 'pass' ? 'hd-banner--pass' : 'hd-banner--fail'">
          <div class="hd-banner__icon">{{ activeReport.result === 'pass' ? '✅' : '❌' }}</div>
          <div class="hd-banner__center">
            <div class="hd-banner__title">{{ activeReport.result === 'pass' ? '水合验证通过' : '水合验证未通过' }}</div>
            <div class="hd-banner__sub">
              T-box {{ activeReport.tboxVersion }} · 17类 · 56关系 · {{ activeReport.customerCount }}实例 · {{ activeReport.scene }}
            </div>
            <div class="hd-banner__checks">
              <span class="hd-banner__chk">✓ 验证项 7/7通过</span>
              <span class="hd-banner__chk">✓ ROI验证达标</span>
              <span class="hd-banner__chk">✓ 逻辑闭环</span>
              <span class="hd-banner__chk">✓ 资源约束</span>
            </div>
          </div>
          <div class="hd-banner__ring">
            <div class="hd-banner__num">{{ activeReport.score }}</div>
            <div class="hd-banner__lbl">综合评分</div>
          </div>
        </div>

        <!-- 关键指标 -->
        <div class="hd-section">
          <div class="hd-stats">
            <div class="hd-stat-card hd-stat-card--blue">
              <div class="hd-stat__num">40,929</div>
              <div class="hd-stat__lbl">客户实例</div>
              <div class="hd-stat__sub">Customer 类</div>
            </div>
            <div class="hd-stat-card hd-stat-card--green">
              <div class="hd-stat__num">40,929</div>
              <div class="hd-stat__lbl">合约实例</div>
              <div class="hd-stat__sub">Contract 类</div>
            </div>
            <div class="hd-stat-card hd-stat-card--amber">
              <div class="hd-stat__num">82,757</div>
              <div class="hd-stat__lbl">工单记录</div>
              <div class="hd-stat__sub">WorkOrder 类</div>
            </div>
            <div class="hd-stat-card hd-stat-card--purple">
              <div class="hd-stat__num">651</div>
              <div class="hd-stat__lbl">成功订单</div>
              <div class="hd-stat__sub">Order 类 · 转化率 0.79%</div>
            </div>
          </div>
        </div>

        <!-- 验证项 -->
        <div class="hd-section">
          <div class="hd-section__title">水合验证项（Hydration Validation）<span class="hd-badge hd-badge--pass">7 / 7 通过</span></div>
          <div class="hd-checklist">
            <table class="hd-mini-table">
              <thead>
                <tr><th>验证项</th><th>规则描述</th><th>结果</th><th>通过数 / 总数</th></tr>
              </thead>
              <tbody>
                <tr v-for="(c, i) in checklist" :key="i">
                  <td><strong>{{ c.name }}</strong></td>
                  <td>{{ c.desc }}</td>
                  <td><span class="hd-badge hd-badge--pass">✅ 通过</span></td>
                  <td><strong style="color:#389e0d">{{ c.passed }}</strong>{{ c.total ? ' / ' + c.total : '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- C05 端到端 -->
        <div class="hd-section">
          <div class="hd-section__title">C05 端到端场景验证</div>
          <div class="hd-pipeline-wrap">
            <div class="hd-pipeline">
              <div class="hd-customer-card">
                <div class="hd-customer__title">演示客户 C05</div>
                <div class="hd-customer__row"><span>user_id</span><span class="hd-mono-sm">101905...5678</span></div>
                <div class="hd-customer__row"><span>contract_id</span><span class="hd-mono-sm">CTR-NMG-001</span></div>
                <div class="hd-customer__row"><span>在网月数</span><span class="hd-mono-sm">45月</span></div>
                <div class="hd-customer__row"><span>剩余合约</span><span class="hd-mono-sm">2月</span></div>
                <div class="hd-customer__seg">Segment: TYPE_1</div>
              </div>
              <div class="hd-pipe-steps">
                <template v-for="(st, i) in pipeSteps" :key="i">
                  <div class="hd-pipe-step">
                    <div class="hd-pipe-step__inner">
                      <div class="hd-pipe-step__num">Step {{ stepLabel(i) }}</div>
                      <div class="hd-pipe-step__title">{{ st.title }}</div>
                      <div class="hd-pipe-step__detail" v-html="st.detail"></div>
                      <div class="hd-pipe-step__result">{{ st.result }}</div>
                    </div>
                  </div>
                  <div v-if="i < pipeSteps.length - 1" class="hd-pipe-arrow">›</div>
                </template>
              </div>
            </div>
            <div class="hd-verdict">
              <span class="hd-verdict__icon">✅</span>
              <span><strong>专家验收：</strong>推理链完整跑通，无孤立节点。SC01推荐符合GROWING期/TYPE_1客户预期，免调测费钩子（FAM_RENEWAL=0元）正确触发，产品推荐在4449行白名单内。C05端到端场景验证通过。</span>
            </div>
          </div>
        </div>

        <!-- ROI -->
        <div class="hd-section">
          <div class="hd-section__title">ROI验证 · 转化率预估 vs 基线</div>
          <div class="hd-roi">
            <div class="hd-roi-card hd-roi-card--baseline">
              <div class="hd-roi__lbl">当前基线</div>
              <div class="hd-roi__num hd-roi__num--baseline">0.79%</div>
              <div class="hd-roi__sub">651成功订单 / 82,757工单（order_result=0000）</div>
              <div class="hd-roi__detail">全量工单转化，未区分策略优先级和客群分层。</div>
            </div>
            <div class="hd-roi-card hd-roi-card--target">
              <div class="hd-roi__lbl">本次优化目标</div>
              <div class="hd-roi__num hd-roi__num--target">1.0%</div>
              <div class="hd-roi__sub">Top 5 策略 × TYPE_1 / TYPE_5 客群</div>
              <div class="hd-roi__detail">
                TYPE_1: 21,648户 · TYPE_5: 19,281户<br />
                精准分层推荐，话术与客群强匹配
              </div>
              <div class="hd-roi__uplift">↑ +0.21pp · 提升幅度 +26.6%</div>
              <table class="hd-mini-table" style="margin-top:12px">
                <thead><tr><th>话术</th><th>目标客群</th><th>预期转化率</th></tr></thead>
                <tbody>
                  <tr><td>SC01 合约临期千兆升级</td><td>GROWING/TYPE_1</td><td class="hd-conv-rate">1.2%</td></tr>
                  <tr><td>SC02 成熟期续约保障</td><td>MATURE/TYPE_5</td><td class="hd-conv-rate">1.5%</td></tr>
                  <tr><td>SC03 长期客高价值保留</td><td>LONG_TERM/TYPE_1</td><td class="hd-conv-rate">2.0%</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- 发布 -->
        <div class="hd-section">
          <div class="hd-section__title">发布本体</div>
          <div class="hd-publish">
            <div class="hd-publish__title">本体已就绪，发布到本体工作室</div>
            <div class="hd-publish__sub">T-box {{ activeReport.tboxVersion }} 将冻结并写入本体工作室，版本快照标注构建路径（双路径·场景驱动+导入驱动），其他省分可从本体集市订购</div>
            <div class="hd-consumers">
              <div class="hd-consumer">
                <div class="hd-consumer__icon">🎯</div>
                <div class="hd-consumer__name">AIP场景平台</div>
                <div class="hd-consumer__desc">消费本体对象<br />编排工作流执行</div>
              </div>
              <div class="hd-consumer">
                <div class="hd-consumer__icon">🤖</div>
                <div class="hd-consumer__name">AI助手</div>
                <div class="hd-consumer__desc">本体查询<br />推理解释</div>
              </div>
              <div class="hd-consumer">
                <div class="hd-consumer__icon">🧪</div>
                <div class="hd-consumer__name">Agent Harness</div>
                <div class="hd-consumer__desc">A/B测试<br />反馈闭环回写</div>
              </div>
              <div class="hd-consumer">
                <div class="hd-consumer__icon">🏙️</div>
                <div class="hd-consumer__name">其他省分</div>
                <div class="hd-consumer__desc">本体集市订购<br />多租户隔离</div>
              </div>
            </div>
            <div class="hd-publish__action">
              <a-button type="primary" size="large" style="background:#389e0d;border-color:#389e0d" @click="goPublish">
                🚀 发布本体 T-box {{ activeReport.tboxVersion }}
              </a-button>
              <div class="hd-publish__note">发布后版本冻结，如需修改请联系本体架构师创建新版本</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建水合演练弹窗 -->
    <a-modal v-model:open="showNew" title="新建水合演练" :footer="null" :width="540">
      <a-form layout="vertical">
        <a-form-item label="T-box 版本">
          <a-input v-model:value="newForm.tboxVersion" placeholder="如：v1.3" />
        </a-form-item>
        <a-form-item label="场景">
          <a-input v-model:value="newForm.scene" placeholder="如：FTTR续约 S2 · 内蒙古" />
        </a-form-item>
        <a-form-item label="客户实例数">
          <a-input v-model:value="newForm.customerCount" placeholder="如：40,929" />
        </a-form-item>
      </a-form>
      <div class="hd-new-tip">
        将立即模拟运行水合验证，过程约 3 秒。
      </div>
      <div style="text-align:right;margin-top:12px">
        <a-space>
          <a-button @click="showNew = false">取消</a-button>
          <a-button type="primary" :loading="running" @click="runNew">开始演练</a-button>
        </a-space>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'

interface DrillRecord {
  id: number
  time: string
  tboxVersion: string
  scene: string
  customerCount: string
  result: 'pass' | 'fail'
  score: number
}

const STORAGE_KEY = 'dataworkshop.hydration.v1'
const router = useRouter()

const records = ref<DrillRecord[]>([])
const filter = ref<'all' | 'pass' | 'fail'>('all')
const search = ref('')
const activeReport = ref<DrillRecord | null>(null)
const showNew = ref(false)
const running = ref(false)

const newForm = reactive({
  tboxVersion: 'v1.3',
  scene: 'FTTR续约 S2 · 内蒙古',
  customerCount: '40,929',
})

const filterOptions = [
  { value: 'all', label: '全部' },
  { value: 'pass', label: '通过' },
  { value: 'fail', label: '失败' },
]

const checklist = [
  { name: 'Customer 实例一致性', desc: 'user_id 与工单表/合约表对齐，无孤立实例', passed: '40,929', total: '40,929' },
  { name: 'Contract 产品约束', desc: 'contract.product_id 在 4449 行产品白名单内', passed: '40,929', total: '40,929' },
  { name: 'WorkOrder 用户关联', desc: 'work_order.user_id 在 Customer 实例集合内', passed: '82,757', total: '82,757' },
  { name: 'Order 工单关联', desc: 'order.work_order_id 对应 WorkOrder 存在', passed: '651', total: '651' },
  { name: 'MarketingMoment 规则覆盖', desc: 'trigger_type 命中 BR-MOMENT-001~004 之一', passed: '4 个规则', total: '' },
  { name: 'Script 客群映射', desc: 'script.target_segment 在 TYPE_1 / TYPE_5 内', passed: '10', total: '10 话术' },
  { name: 'Strategy 客群对齐', desc: 'Strategy → appliesToSegment → TYPE_1 / TYPE_5', passed: 'Segment', total: '命名已校准' },
]

const pipeSteps = [
  { title: '水合读取', detail: 'Contract.remaining_months = 2<br>is_expiring_soon = true', result: '合约剩余2月 ✓' },
  { title: '规则触发', detail: 'BR-MOMENT-001<br>remaining ≤ 3月', result: 'CONTRACT_EXPIRY ✓' },
  { title: '账期匹配', detail: 'innet_months = 45月<br>account_period = GROWING', result: 'GROWING期 ✓' },
  { title: '话术推荐', detail: 'Script = SC01<br>免调测费钩子', result: '合约临期千兆升级 ✓' },
  { title: '产品推荐', detail: '联通FTTR千兆<br>宽带299元套餐', result: 'FAM_RENEWAL=0元 ✓' },
]

const filtered = computed(() => {
  const kw = search.value.toLowerCase().trim()
  return records.value.filter((r) => {
    if (filter.value !== 'all' && r.result !== filter.value) return false
    if (!kw) return true
    return [r.tboxVersion, r.scene, r.time].some((s) => s.toLowerCase().includes(kw))
  })
})

function scoreClass(s: number) {
  if (s >= 85) return 'high'
  if (s >= 70) return 'mid'
  return 'low'
}

function stepLabel(i: number) {
  const map = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧']
  return map[i] || (i + 1)
}

function reportNo(r: DrillRecord) {
  return 'RPT-' + r.time.replace(/\D/g, '').slice(0, 8) + '-' + String(r.id).padStart(3, '0')
}

function openReport(r: DrillRecord) {
  activeReport.value = r
  window.scrollTo(0, 0)
}

function goPublish() {
  router.push('/ontology/publish')
}

function loadPersisted(): DrillRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) { /* ignore */ }
  return seed()
}
function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records.value))
}
function seed(): DrillRecord[] {
  return [
    { id: 1, time: '2026-04-25 14:32', tboxVersion: 'v1.2', scene: 'FTTR续约 S2 · 内蒙古', customerCount: '40,929', result: 'pass', score: 94 },
    { id: 2, time: '2026-04-18 10:15', tboxVersion: 'v1.1', scene: 'FTTR续约 S2 · 内蒙古', customerCount: '38,741', result: 'pass', score: 91 },
    { id: 3, time: '2026-04-10 16:04', tboxVersion: 'v1.1', scene: 'FTTR续约 S1 · 内蒙古', customerCount: '35,200', result: 'pass', score: 88 },
    { id: 4, time: '2026-04-02 09:51', tboxVersion: 'v1.0', scene: 'FTTR续约 S2 · 内蒙古', customerCount: '32,015', result: 'fail', score: 61 },
    { id: 5, time: '2026-03-20 14:22', tboxVersion: 'v1.0', scene: 'FTTR续约 S1 · 内蒙古', customerCount: '30,889', result: 'pass', score: 85 },
    { id: 6, time: '2026-03-01 11:08', tboxVersion: 'v0.9', scene: 'FTTR续约 S1 · 内蒙古', customerCount: '28,400', result: 'pass', score: 79 },
  ]
}

function startNewDrill() { showNew.value = true }

async function runNew() {
  if (!newForm.tboxVersion.trim() || !newForm.scene.trim() || !newForm.customerCount.trim()) {
    message.warning('请填写完整信息'); return
  }
  running.value = true
  await new Promise((r) => setTimeout(r, 2400))
  const score = 78 + Math.floor(Math.random() * 18)
  const result: 'pass' | 'fail' = score >= 70 ? 'pass' : 'fail'
  const now = new Date()
  const pad = (n: number) => (n < 10 ? '0' + n : '' + n)
  const time = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
  const id = Math.max(0, ...records.value.map((r) => r.id)) + 1
  records.value = [{ id, time, tboxVersion: newForm.tboxVersion, scene: newForm.scene, customerCount: newForm.customerCount, result, score }, ...records.value]
  persist()
  running.value = false
  showNew.value = false
  message.success('演练完成，得分 ' + score)
}

onMounted(() => { records.value = loadPersisted() })
</script>

<style scoped>
.hd-tab { background: var(--neutral-50); padding: 16px; border-radius: 12px; min-height: 60vh; }

/* 列表视图 */
.hd-title-area { margin-bottom: 16px; }
.hd-title { font-size: 16px; font-weight: 700; color: var(--neutral-900); }
.hd-subtitle { font-size: 12px; color: var(--neutral-600); margin-top: 2px; }

.hd-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }

.hd-table-wrap {
  background: #fff; border: 1px solid var(--neutral-200); border-radius: 8px;
  overflow: hidden; box-shadow: var(--shadow-xs);
}
.hd-table { width: 100%; border-collapse: collapse; }
.hd-table thead th {
  background: #fafafa; padding: 10px 14px; text-align: left;
  font-size: 11px; font-weight: 600; color: var(--neutral-600);
  border-bottom: 1px solid var(--neutral-200); white-space: nowrap;
}
.hd-table tbody td {
  padding: 11px 14px; font-size: 12px; color: var(--neutral-700);
  border-bottom: 1px solid var(--neutral-100); vertical-align: middle;
}
.hd-table tbody tr:last-child td { border-bottom: none; }
.hd-table tbody tr:hover td { background: #fafafa; cursor: pointer; }
.hd-table tr.row-fail { border-left: 3px solid #ff4d4f; }
.hd-table tr.row-fail td:first-child { padding-left: 11px; }

.hd-num { color: var(--neutral-500); }
.hd-mono { font-family: var(--font-mono); font-size: 11px; }
.hd-bold { font-weight: 600; }
.hd-version { background: #e6f4ff; color: #1890ff; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }

.hd-badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.hd-badge--pass { background: #d9f7be; color: #389e0d; }
.hd-badge--fail { background: #fff1f0; color: #cf1322; }

.hd-score { display: inline-flex; align-items: center; gap: 6px; font-weight: 700; color: var(--neutral-900); }
.hd-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.hd-dot.high { background: #52c41a; }
.hd-dot.mid { background: #fa8c16; }
.hd-dot.low { background: #ff4d4f; }

.hd-empty { text-align: center; padding: 32px; color: var(--neutral-400); font-size: 12px; }

/* 报告视图 */
.hd-report-bar {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  background: #fff; border: 1px solid var(--neutral-200); border-radius: 8px;
  padding: 10px 16px; margin-bottom: 16px;
}
.hd-breadcrumb { font-size: 12px; color: var(--neutral-500); }
.hd-breadcrumb span { color: var(--neutral-800); font-weight: 600; }
.hd-meta { font-size: 11px; color: var(--neutral-500); margin-right: 4px; }

.hd-report-body { display: flex; flex-direction: column; gap: 20px; }

.hd-banner {
  border-radius: 12px; padding: 20px 28px; display: flex; align-items: center; gap: 24px;
  color: #fff;
}
.hd-banner--pass { background: linear-gradient(135deg, #389e0d 0%, #52c41a 60%, #34d399 100%); }
.hd-banner--fail { background: linear-gradient(135deg, #cf1322 0%, #ff4d4f 60%, #ff7875 100%); }
.hd-banner__icon { font-size: 40px; flex-shrink: 0; }
.hd-banner__center { flex: 1; }
.hd-banner__title { font-size: 20px; font-weight: 800; margin-bottom: 4px; }
.hd-banner__sub { font-size: 12px; opacity: 0.85; margin-bottom: 10px; }
.hd-banner__checks { display: flex; gap: 16px; flex-wrap: wrap; }
.hd-banner__chk {
  display: inline-flex; align-items: center; gap: 5px; font-size: 11px;
  background: rgba(255, 255, 255, 0.2); border-radius: 16px; padding: 3px 10px;
}
.hd-banner__ring {
  width: 72px; height: 72px; border-radius: 50%;
  background: rgba(255, 255, 255, 0.2); border: 4px solid rgba(255, 255, 255, 0.6);
  display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0;
}
.hd-banner__num { font-size: 22px; font-weight: 800; line-height: 1; }
.hd-banner__lbl { font-size: 10px; opacity: 0.8; }

/* Section 公共 */
.hd-section { background: transparent; }
.hd-section__title {
  font-size: 13px; font-weight: 700; color: var(--neutral-900);
  margin-bottom: 12px; display: flex; align-items: center; gap: 8px;
}
.hd-section__title::before {
  content: ''; width: 3px; height: 15px; background: #1890ff;
  border-radius: 2px; display: inline-block;
}

/* 统计卡 */
.hd-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.hd-stat-card {
  background: #fff; border: 1px solid var(--neutral-200); border-radius: 8px; padding: 14px 18px;
}
.hd-stat-card--blue { border-left: 3px solid #1890ff; }
.hd-stat-card--green { border-left: 3px solid #52c41a; }
.hd-stat-card--amber { border-left: 3px solid #fa8c16; }
.hd-stat-card--purple { border-left: 3px solid #722ed1; }
.hd-stat__num { font-size: 24px; font-weight: 800; color: var(--neutral-900); line-height: 1.1; }
.hd-stat__lbl { font-size: 11px; color: var(--neutral-600); margin-top: 3px; }
.hd-stat__sub { font-size: 10px; color: var(--neutral-400); margin-top: 2px; }

/* 验证项表 */
.hd-checklist { background: #fff; border: 1px solid var(--neutral-200); border-radius: 8px; overflow: hidden; }
.hd-mini-table { width: 100%; border-collapse: collapse; }
.hd-mini-table thead th {
  background: #fafafa; padding: 9px 14px; text-align: left;
  font-size: 11px; font-weight: 600; color: var(--neutral-600);
  border-bottom: 1px solid var(--neutral-200);
}
.hd-mini-table tbody td {
  padding: 10px 14px; font-size: 12px; color: var(--neutral-700);
  border-bottom: 1px solid var(--neutral-100); vertical-align: middle;
}
.hd-mini-table tbody tr:last-child td { border-bottom: none; }
.hd-conv-rate { color: #389e0d; font-weight: 700; }

/* C05 端到端 */
.hd-pipeline-wrap { background: #fff; border: 1px solid var(--neutral-200); border-radius: 10px; padding: 20px 24px; }
.hd-pipeline { display: flex; align-items: stretch; gap: 20px; }
.hd-customer-card {
  background: #fafafa; border: 1px solid var(--neutral-200); border-radius: 8px;
  padding: 14px; width: 180px; flex-shrink: 0;
}
.hd-customer__title {
  font-size: 11px; font-weight: 700; color: var(--neutral-600);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;
}
.hd-customer__row {
  display: flex; justify-content: space-between; padding: 3px 0;
  font-size: 11px; border-bottom: 1px solid var(--neutral-100);
}
.hd-customer__row:last-of-type { border-bottom: none; }
.hd-customer__row > span:first-child { color: var(--neutral-600); }
.hd-customer__row > span:last-child { color: var(--neutral-900); font-weight: 600; }
.hd-mono-sm { font-family: var(--font-mono); font-size: 10px; }
.hd-customer__seg {
  margin-top: 8px; background: #e6f4ff; border-radius: 4px;
  padding: 4px 8px; font-size: 11px; color: #1890ff; font-weight: 600; text-align: center;
}

.hd-pipe-steps { flex: 1; display: flex; align-items: center; gap: 0; }
.hd-pipe-step { flex: 1; }
.hd-pipe-step__inner {
  background: #fff; border: 1.5px solid #1890ff; border-radius: 8px;
  padding: 10px 12px; margin: 0 4px;
}
.hd-pipe-step__num { font-size: 10px; color: #1890ff; font-weight: 700; margin-bottom: 4px; }
.hd-pipe-step__title { font-size: 11px; font-weight: 700; color: var(--neutral-900); margin-bottom: 4px; line-height: 1.3; }
.hd-pipe-step__detail { font-size: 10px; color: var(--neutral-600); line-height: 1.5; }
.hd-pipe-step__result {
  font-size: 10px; color: #389e0d; font-weight: 600;
  margin-top: 4px; padding-top: 4px; border-top: 1px solid var(--neutral-100);
}
.hd-pipe-arrow { color: #1890ff; font-size: 18px; flex-shrink: 0; margin: 0 -2px; z-index: 1; }

.hd-verdict {
  background: #f6ffed; border: 1.5px solid #95de64; border-radius: 8px;
  padding: 12px 16px; margin-top: 14px;
  display: flex; align-items: flex-start; gap: 8px;
  font-size: 11px; color: #135200; line-height: 1.7;
}
.hd-verdict__icon { font-size: 16px; flex-shrink: 0; }

/* ROI */
.hd-roi { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.hd-roi-card { border-radius: 10px; padding: 20px 24px; }
.hd-roi-card--baseline { background: #fafafa; border: 1px solid var(--neutral-200); }
.hd-roi-card--target { background: linear-gradient(135deg, #e6f4ff, #f6ffed); border: 1.5px solid #95de64; }
.hd-roi__lbl { font-size: 12px; color: var(--neutral-600); }
.hd-roi__num { font-size: 36px; font-weight: 900; line-height: 1; margin: 8px 0 4px; }
.hd-roi__num--baseline { color: var(--neutral-500); }
.hd-roi__num--target { color: #389e0d; }
.hd-roi__sub { font-size: 11px; color: var(--neutral-400); margin-bottom: 12px; }
.hd-roi__detail { font-size: 11px; color: var(--neutral-700); line-height: 1.7; }
.hd-roi__uplift {
  display: inline-flex; align-items: center; gap: 4px;
  background: #d9f7be; color: #389e0d; border-radius: 12px;
  padding: 2px 10px; font-size: 11px; font-weight: 700; margin-top: 6px;
}

/* 发布 */
.hd-publish { background: #fff; border: 2px solid #1890ff; border-radius: 12px; padding: 24px 28px; }
.hd-publish__title { font-size: 15px; font-weight: 800; color: var(--neutral-900); margin-bottom: 4px; }
.hd-publish__sub { font-size: 12px; color: var(--neutral-600); margin-bottom: 20px; }
.hd-consumers { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
.hd-consumer {
  background: #fafafa; border: 1px solid var(--neutral-200); border-radius: 8px;
  padding: 10px; text-align: center;
}
.hd-consumer__icon { font-size: 20px; margin-bottom: 4px; }
.hd-consumer__name { font-size: 11px; font-weight: 600; color: var(--neutral-700); margin-bottom: 2px; }
.hd-consumer__desc { font-size: 10px; color: var(--neutral-400); }
.hd-publish__action { text-align: center; }
.hd-publish__note { font-size: 10px; color: var(--neutral-400); margin-top: 8px; }

.hd-new-tip { font-size: 12px; color: var(--neutral-500); padding: 10px 12px; background: var(--neutral-50); border-radius: 6px; }
</style>
