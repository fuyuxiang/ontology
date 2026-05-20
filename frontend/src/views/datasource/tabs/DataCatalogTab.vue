<template>
  <div class="cat-tab">
    <div class="cat-toolbar">
      <a-input v-model:value="search" placeholder="搜索数据集..." allow-clear style="width: 280px">
        <template #prefix><span style="color:#bfbfbf">🔍</span></template>
      </a-input>
      <a-select v-model:value="tagFilter" placeholder="按标签筛选" allow-clear style="width: 140px" :options="tagOptions" />
      <span style="flex:1"></span>
      <span class="cat-count">共 {{ filtered.length }} 个数据集</span>
    </div>

    <div class="cat-grid">
      <div v-for="d in filtered" :key="d.key" class="cat-card" @click="openDetail(d)">
        <div class="cat-card__head">
          <span class="cat-card__name">{{ d.name }}</span>
          <a-tag color="purple" style="font-size:11px;margin-left:8px">@{{ d.ontology }}</a-tag>
          <a-tag :color="d.matched ? 'success' : 'default'" style="font-size:11px">{{ d.matched ? '已对应' : '待确认' }}</a-tag>
        </div>
        <div class="cat-card__desc">{{ d.desc }}</div>
        <div class="cat-card__tags">
          <a-tag v-for="t in d.tags" :key="t" style="font-size:11px">{{ t }}</a-tag>
        </div>
        <div class="cat-card__meta">
          <span>记录: {{ d.records }}</span>
          <span>频率: {{ d.freq }}</span>
        </div>
        <div class="cat-card__owner">所有者: {{ d.owner }}</div>
      </div>
    </div>

    <a-modal v-model:open="showDetail" :title="selected?.name" :width="640" :footer="null">
      <div v-if="selected" class="cat-detail">
        <div class="cat-detail__row"><span>本体对象</span><strong>@{{ selected.ontology }}</strong></div>
        <div class="cat-detail__row"><span>记录条数</span><strong>{{ selected.records }}</strong></div>
        <div class="cat-detail__row"><span>更新频率</span><strong>{{ selected.freq }}</strong></div>
        <div class="cat-detail__row"><span>所有者</span><strong>{{ selected.owner }}</strong></div>
        <div class="cat-detail__row"><span>描述</span><div style="flex:1;color:#475569">{{ selected.desc }}</div></div>
        <div class="cat-detail__row" style="align-items:flex-start"><span>标签</span>
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            <a-tag v-for="t in selected.tags" :key="t">{{ t }}</a-tag>
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Dataset {
  key: string
  name: string
  englishName: string
  ontology: string
  desc: string
  tags: string[]
  records: string
  freq: string
  owner: string
  matched: boolean
}

const search = ref('')
const tagFilter = ref<string | undefined>(undefined)
const showDetail = ref(false)
const selected = ref<Dataset | null>(null)

const datasets: Dataset[] = [
  { key: 'd1', name: 'CBSS用户信息主表', englishName: 'dwa_v_d_cus_cb_user_info', ontology: 'Customer', desc: '客户基础信息（姓名/年龄/在网月数/客户等级），FTTR续约场景核心人口属性来源', tags: ['核心', '客户'], records: '40,929', freq: '日更', owner: '客户中心 · 张三', matched: true },
  { key: 'd2', name: 'CBSS活动合约系统', englishName: 'dwa_v_d_cus_cb_act_info', ontology: 'Contract', desc: '合约产品订购、合约期、产品白名单（4449行产品）', tags: ['合约', '日更'], records: '40,929', freq: '日更', owner: '合约管理 · 李四', matched: true },
  { key: 'd3', name: '客服工单系统', englishName: 'dwd_d_evt_kf_order_main', ontology: 'WorkOrder', desc: '客服工单全量记录，order_result 区分成功/失败订单', tags: ['工单'], records: '82,757', freq: '小时更', owner: '客服中心', matched: true },
  { key: 'd4', name: 'CBSS出账系统', englishName: 'dwa_v_m_cus_cb_sing_charge', ontology: 'Charge', desc: '出账记录、月度费用与缴费状态', tags: ['计费', '月更'], records: '124,830', freq: '月更', owner: '计费中心', matched: false },
  { key: 'd5', name: '欠费信息系统', englishName: 'dwd_m_mrt_al_chl_owe', ontology: 'Arrears', desc: '欠费明细、欠费时长', tags: ['计费'], records: '8,201', freq: '日更', owner: '催缴组', matched: false },
  { key: 'd6', name: '语音详单系统', englishName: 'dwd_d_use_cb_f_voice', ontology: 'CallDetail', desc: '语音通话详单（通话时长、对端号码）', tags: ['网络'], records: '待业务方提供', freq: '日更', owner: '网络中心', matched: false },
  { key: 'd7', name: '携转资格查询系统', englishName: 'dwd_d_cus_np_turn_query_user', ontology: 'PortabilityQuery', desc: '携号转网资格查询日志', tags: ['MNP'], records: '15,440', freq: '日更', owner: 'MNP组', matched: true },
  { key: 'd8', name: '全客携转维系系统', englishName: 'dwd_d_cus_qk_turn_maintain', ontology: 'RetentionRecord', desc: '维系客户跟进记录', tags: ['MNP', '维系'], records: '6,128', freq: '日更', owner: 'MNP组', matched: true },
  { key: 'd9', name: '融合业务信息系统', englishName: 'DWA_V_D_CUS_CB_OM_DATUM', ontology: 'BundleProduct', desc: '融合套餐订购明细', tags: ['套餐'], records: '52,340', freq: '日更', owner: '产品组', matched: true },
  { key: 'd10', name: '携转预警结果存储', englishName: 't_mnp_risk_warning', ontology: 'RiskWarning', desc: '模型推理后的高风险用户名单', tags: ['MNP', '模型'], records: '1,284', freq: '日更', owner: 'MNP组', matched: true },
]

const allTags = computed(() => {
  const set = new Set<string>()
  datasets.forEach((d) => d.tags.forEach((t) => set.add(t)))
  return Array.from(set)
})
const tagOptions = computed(() => allTags.value.map((t) => ({ value: t, label: t })))

const filtered = computed(() => {
  const kw = search.value.trim().toLowerCase()
  return datasets.filter((d) => {
    if (tagFilter.value && !d.tags.includes(tagFilter.value)) return false
    if (!kw) return true
    return [d.name, d.englishName, d.ontology, d.desc].some((s) => s.toLowerCase().includes(kw))
  })
})

function openDetail(d: Dataset) { selected.value = d; showDetail.value = true }
</script>

<style scoped>
.cat-tab { display: flex; flex-direction: column; gap: 16px; }
.cat-toolbar { display: flex; align-items: center; gap: 12px; }
.cat-count { font-size: 12px; color: var(--neutral-500); }

.cat-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;
}
.cat-card {
  background: #fff; border: 1px solid var(--neutral-200); border-radius: 10px;
  padding: 16px; cursor: pointer; transition: all var(--transition-fast);
}
.cat-card:hover {
  border-color: var(--semantic-300); box-shadow: var(--shadow-sm); transform: translateY(-1px);
}
.cat-card__head { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
.cat-card__name { font-weight: 600; font-size: 14px; color: var(--neutral-900); }
.cat-card__desc {
  font-size: 12px; color: var(--neutral-600); margin-bottom: 8px;
  line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden;
}
.cat-card__tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
.cat-card__meta {
  display: flex; justify-content: space-between;
  font-size: 12px; color: var(--neutral-500);
}
.cat-card__owner { font-size: 11px; color: var(--neutral-500); margin-top: 4px; }

.cat-detail { display: flex; flex-direction: column; gap: 8px; }
.cat-detail__row {
  display: flex; gap: 16px; padding: 8px 0;
  border-bottom: 1px solid var(--neutral-100); font-size: 13px;
}
.cat-detail__row:last-child { border-bottom: none; }
.cat-detail__row > span:first-child { width: 80px; color: var(--neutral-500); flex-shrink: 0; }
</style>
