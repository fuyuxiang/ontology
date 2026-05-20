<template>
  <div class="ln-tab">
    <div class="ln-header">
      <div>
        <div class="ln-title">数据血缘追踪</div>
        <div class="ln-subtitle">按行对齐数据源 → ETL → 本体 → 应用；点击本体节点查看字段级血缘</div>
      </div>
      <a-input v-model:value="search" placeholder="搜索节点..." allow-clear style="width: 240px" />
    </div>

    <div class="ln-canvas">
      <!-- 列：数据源 -->
      <div class="ln-col">
        <div class="ln-col__title">数据源</div>
        <div v-for="n in filteredCol('source')" :key="n.id" class="ln-node ln-node--source" @click="select(n)" :class="{ 'ln-node--active': selected?.id === n.id }">
          <div class="ln-node__icon">🗄️</div>
          <div class="ln-node__body">
            <div class="ln-node__name">{{ n.name }}</div>
            <div class="ln-node__sub">{{ n.sub }}</div>
          </div>
        </div>
      </div>
      <div class="ln-col-arrow">→</div>

      <!-- 列：ETL -->
      <div class="ln-col">
        <div class="ln-col__title">ETL 加工</div>
        <div v-for="n in filteredCol('etl')" :key="n.id" class="ln-node ln-node--etl" @click="select(n)" :class="{ 'ln-node--active': selected?.id === n.id }">
          <div class="ln-node__icon">⚙️</div>
          <div class="ln-node__body">
            <div class="ln-node__name">{{ n.name }}</div>
            <div class="ln-node__sub">{{ n.sub }}</div>
          </div>
        </div>
      </div>
      <div class="ln-col-arrow">→</div>

      <!-- 列：本体 -->
      <div class="ln-col">
        <div class="ln-col__title">本体对象</div>
        <div v-for="n in filteredCol('ontology')" :key="n.id" class="ln-node ln-node--ontology" @click="select(n)" :class="{ 'ln-node--active': selected?.id === n.id }">
          <div class="ln-node__icon">⚛️</div>
          <div class="ln-node__body">
            <div class="ln-node__name">{{ n.name }}</div>
            <div class="ln-node__sub">{{ n.sub }}</div>
          </div>
        </div>
      </div>
      <div class="ln-col-arrow">→</div>

      <!-- 列：应用 -->
      <div class="ln-col">
        <div class="ln-col__title">应用消费</div>
        <div v-for="n in filteredCol('app')" :key="n.id" class="ln-node ln-node--app" @click="select(n)" :class="{ 'ln-node--active': selected?.id === n.id }">
          <div class="ln-node__icon">📊</div>
          <div class="ln-node__body">
            <div class="ln-node__name">{{ n.name }}</div>
            <div class="ln-node__sub">{{ n.sub }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 字段级血缘 -->
    <div v-if="selected" class="ln-detail">
      <div class="ln-detail__title">
        <span>{{ selected.name }}</span>
        <a-button size="small" @click="selected = null">关闭</a-button>
      </div>
      <div class="ln-detail__sub">字段级血缘 / 字段映射</div>
      <table class="ln-detail__table">
        <thead>
          <tr><th>字段</th><th>类型</th><th>映射来源</th><th>转换</th></tr>
        </thead>
        <tbody>
          <tr v-for="(f, i) in (selected.fields || [])" :key="i">
            <td><strong>{{ f.field }}</strong></td>
            <td>{{ f.type }}</td>
            <td><span class="ln-mono">{{ f.from }}</span></td>
            <td>{{ f.transform || '直接映射' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Field { field: string; type: string; from: string; transform?: string }
interface LineageNode {
  id: string
  type: 'source' | 'etl' | 'ontology' | 'app'
  name: string
  sub: string
  fields?: Field[]
}

const search = ref('')
const selected = ref<LineageNode | null>(null)

const nodes: LineageNode[] = [
  { id: 's1', type: 'source', name: 'CBSS用户信息主表', sub: 'dwa_v_d_cus_cb_user_info' },
  { id: 's2', type: 'source', name: 'CBSS活动合约系统', sub: 'dwa_v_d_cus_cb_act_info' },
  { id: 's3', type: 'source', name: '客服工单系统', sub: 'dwd_d_evt_kf_order_main' },
  { id: 's4', type: 'source', name: '出账系统', sub: 'dwa_v_m_cus_cb_sing_charge' },

  { id: 'e1', type: 'etl', name: '客户主数据加工', sub: 'pl-customer-001' },
  { id: 'e2', type: 'etl', name: '合约清洗加工', sub: 'pl-contract-001' },
  { id: 'e3', type: 'etl', name: '工单去重映射', sub: 'pl-workorder-001' },
  { id: 'e4', type: 'etl', name: '出账聚合', sub: 'pl-charge-agg' },

  {
    id: 'o1', type: 'ontology', name: 'Customer 客户', sub: '17 字段 · 40,929 实例',
    fields: [
      { field: 'user_id', type: 'STRING', from: 'cb_user_info.user_id', transform: '直接映射' },
      { field: 'name', type: 'STRING', from: 'cb_user_info.name', transform: '脱敏（保留首字 + ***）' },
      { field: 'innet_months', type: 'INT', from: 'cb_user_info.in_net_date', transform: 'datediff(now, in_net_date)/30' },
      { field: 'segment', type: 'ENUM', from: '规则引擎 BR-SEG-001', transform: 'TYPE_1 / TYPE_5 推导' },
      { field: 'churn_risk', type: 'FLOAT', from: 'tag_churn_risk', transform: '模型推理打分' },
    ],
  },
  {
    id: 'o2', type: 'ontology', name: 'Contract 合约', sub: '12 字段 · 40,929 实例',
    fields: [
      { field: 'contract_id', type: 'STRING', from: 'cb_act_info.act_id', transform: '直接映射' },
      { field: 'product_id', type: 'STRING', from: 'cb_act_info.prod_id' },
      { field: 'remaining_months', type: 'INT', from: 'cb_act_info.end_date', transform: 'datediff(end_date, now)/30' },
      { field: 'is_expiring_soon', type: 'BOOL', from: 'remaining_months', transform: 'remaining_months <= 3' },
    ],
  },
  { id: 'o3', type: 'ontology', name: 'WorkOrder 工单', sub: '8 字段 · 82,757 实例' },
  { id: 'o4', type: 'ontology', name: 'Order 订单', sub: '6 字段 · 651 实例' },

  { id: 'a1', type: 'app', name: 'AIP场景平台', sub: 'FTTR续约场景' },
  { id: 'a2', type: 'app', name: 'AI助手', sub: '本体查询' },
  { id: 'a3', type: 'app', name: 'Agent Harness', sub: 'A/B 测试' },
  { id: 'a4', type: 'app', name: 'OSDK 服务', sub: '业务系统消费' },
]

function filteredCol(t: LineageNode['type']) {
  const kw = search.value.trim().toLowerCase()
  return nodes.filter((n) => n.type === t && (!kw || n.name.toLowerCase().includes(kw) || n.sub.toLowerCase().includes(kw)))
}

function select(n: LineageNode) { selected.value = n }
</script>

<style scoped>
.ln-tab { display: flex; flex-direction: column; gap: 16px; }
.ln-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.ln-title { font-size: 14px; font-weight: 600; color: var(--neutral-900); }
.ln-subtitle { font-size: 12px; color: var(--neutral-500); margin-top: 2px; }

.ln-canvas {
  display: flex; align-items: stretch; gap: 0;
  background: #fff; border: 1px solid var(--neutral-200); border-radius: 12px;
  padding: 24px; min-height: 480px; overflow-x: auto;
}
.ln-col { flex: 1; min-width: 200px; display: flex; flex-direction: column; gap: 10px; }
.ln-col__title {
  font-size: 12px; font-weight: 600; color: var(--neutral-600);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;
  padding-bottom: 8px; border-bottom: 1px solid var(--neutral-100);
}
.ln-col-arrow {
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; color: var(--neutral-300); padding: 0 8px;
}

.ln-node {
  display: flex; align-items: center; gap: 8px;
  background: #fff; border: 1px solid var(--neutral-200); border-radius: 8px;
  padding: 10px 12px; cursor: pointer; transition: all var(--transition-fast);
}
.ln-node:hover { box-shadow: var(--shadow-sm); }
.ln-node--active { border-color: var(--semantic-500); box-shadow: 0 0 0 2px rgba(76, 110, 245, 0.18); }
.ln-node__icon { font-size: 18px; flex-shrink: 0; }
.ln-node__body { flex: 1; min-width: 0; }
.ln-node__name { font-size: 12px; font-weight: 600; color: var(--neutral-900); }
.ln-node__sub { font-size: 11px; color: var(--neutral-500); margin-top: 2px; word-break: break-all; }

.ln-node--source { border-left: 3px solid #3b82f6; }
.ln-node--etl { border-left: 3px solid #f59e0b; }
.ln-node--ontology { border-left: 3px solid #7c3aed; }
.ln-node--app { border-left: 3px solid #10b981; }

.ln-detail { background: #fff; border: 1px solid var(--neutral-200); border-radius: 12px; padding: 18px 20px; }
.ln-detail__title {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 14px; font-weight: 600; color: var(--neutral-900); margin-bottom: 4px;
}
.ln-detail__sub { font-size: 12px; color: var(--neutral-500); margin-bottom: 12px; }
.ln-detail__table { width: 100%; border-collapse: collapse; }
.ln-detail__table thead th {
  background: var(--neutral-50); padding: 8px 12px; text-align: left;
  font-size: 11px; color: var(--neutral-600); border-bottom: 1px solid var(--neutral-200);
}
.ln-detail__table tbody td {
  padding: 8px 12px; font-size: 12px; color: var(--neutral-700);
  border-bottom: 1px solid var(--neutral-100);
}
.ln-mono { font-family: var(--font-mono); font-size: 11px; }
</style>
