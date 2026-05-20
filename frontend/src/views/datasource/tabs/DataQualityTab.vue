<template>
  <div class="ql-tab">
    <a-row :gutter="16" style="margin-bottom: 20px">
      <!-- 综合质量评分 -->
      <a-col :span="6">
        <div class="ql-card">
          <div class="ql-card__title">综合质量评分</div>
          <div class="ql-progress">
            <a-progress type="dashboard" :percent="91.2" :stroke-color="{ '0%': '#1890ff', '100%': '#52c41a' }" :stroke-width="7" :width="110">
              <template #format>
                <div style="text-align:center">
                  <div style="font-size:26px;font-weight:700;color:#262626">91%</div>
                </div>
              </template>
            </a-progress>
          </div>
          <div class="ql-card__row">
            <div class="ql-card__cell"><div class="ql-cell__num" style="color:#1890ff">5</div><div class="ql-cell__lbl">通道</div></div>
            <div class="ql-card__cell" style="border-left:1px solid #f0f0f0"><div class="ql-cell__num" style="color:#1890ff">6</div><div class="ql-cell__lbl">对齐</div></div>
            <div class="ql-card__cell" style="border-left:1px solid #f0f0f0"><div class="ql-cell__num" style="color:#fa8c16">↑0.9</div><div class="ql-cell__lbl">发展</div></div>
          </div>
        </div>
      </a-col>

      <!-- 维度分布 -->
      <a-col :span="9">
        <div class="ql-card">
          <div class="ql-card__title">质量维度分布</div>
          <div class="ql-card__sub">各维度得分及改善建议</div>
          <div class="ql-dims">
            <div v-for="d in dimensions" :key="d.name" class="ql-dim">
              <div class="ql-dim__name">{{ d.name }}</div>
              <div class="ql-dim__bar">
                <div class="ql-dim__fill" :style="{ width: d.score + '%', background: d.color }"></div>
              </div>
              <div class="ql-dim__score" :style="{ color: d.color }">{{ d.score }}</div>
            </div>
          </div>
        </div>
      </a-col>

      <!-- 异常监控 -->
      <a-col :span="9">
        <div class="ql-card">
          <div class="ql-card__title">异常监控</div>
          <div class="ql-card__sub">最近 7 天数据质量异常</div>
          <ul class="ql-alerts">
            <li v-for="(a, i) in alerts" :key="i" class="ql-alert" :class="'ql-alert--' + a.level">
              <div class="ql-alert__icon">{{ a.level === 'high' ? '⚠️' : a.level === 'mid' ? '⚡' : 'ℹ️' }}</div>
              <div class="ql-alert__body">
                <div class="ql-alert__title">{{ a.title }}</div>
                <div class="ql-alert__desc">{{ a.desc }}</div>
              </div>
              <div class="ql-alert__time">{{ a.time }}</div>
            </li>
          </ul>
        </div>
      </a-col>
    </a-row>

    <!-- 数据集质量明细 -->
    <div class="ql-card" style="padding: 0">
      <div style="padding: 16px 20px; border-bottom: 1px solid var(--neutral-100)">
        <div class="ql-card__title">数据集质量明细</div>
      </div>
      <a-table :columns="cols" :data-source="datasets" :pagination="false" size="middle" row-key="key">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'score'">
            <div class="ql-score">
              <div class="ql-score__bar"><div class="ql-score__fill" :style="{ width: record.score + '%', background: scoreColor(record.score) }"></div></div>
              <span class="ql-score__num" :style="{ color: scoreColor(record.score) }">{{ record.score }}</span>
            </div>
          </template>
          <template v-else-if="column.key === 'completeness'">{{ record.completeness }}%</template>
          <template v-else-if="column.key === 'accuracy'">{{ record.accuracy }}%</template>
          <template v-else-if="column.key === 'timeliness'">{{ record.timeliness }}%</template>
          <template v-else-if="column.key === 'consistency'">{{ record.consistency }}%</template>
        </template>
      </a-table>
    </div>
  </div>
</template>

<script setup lang="ts">

const dimensions = [
  { name: '完整性', score: 96.8, color: '#52c41a' },
  { name: '准确性', score: 93.4, color: '#52c41a' },
  { name: '及时性', score: 89.7, color: '#fa8c16' },
  { name: '一致性', score: 91.5, color: '#52c41a' },
  { name: '唯一性', score: 88.2, color: '#fa8c16' },
  { name: '合规性', score: 95.1, color: '#52c41a' },
]

const alerts = [
  { level: 'high', title: 'Customer.phone 非空率告警', desc: '昨日批次中 phone 字段空值率 5.2%，超过阈值 2%', time: '2 小时前' },
  { level: 'mid', title: 'WorkOrder 工单时延异常', desc: '近 1 小时工单数据延迟到达，平均延迟 12 分钟', time: '4 小时前' },
  { level: 'low', title: 'Contract 主键重复检测', desc: '检测到 3 条 contract_id 主键重复，已自动去重', time: '昨天 18:03' },
  { level: 'low', title: '语音详单数据补齐', desc: '业务方已确认数据补齐排期，预计本周内', time: '昨天 10:15' },
]

const datasets = [
  { key: 'd1', name: 'CBSS用户信息主表', records: '40,929', score: 94, completeness: 99.2, accuracy: 96.8, timeliness: 92.5, consistency: 91.0 },
  { key: 'd2', name: 'CBSS活动合约系统', records: '40,929', score: 92, completeness: 98.7, accuracy: 95.4, timeliness: 90.0, consistency: 90.4 },
  { key: 'd3', name: '客服工单系统', records: '82,757', score: 88, completeness: 96.5, accuracy: 92.1, timeliness: 84.2, consistency: 89.0 },
  { key: 'd4', name: 'CBSS出账系统', records: '124,830', score: 91, completeness: 97.8, accuracy: 94.0, timeliness: 88.5, consistency: 91.5 },
  { key: 'd5', name: '欠费信息系统', records: '8,201', score: 85, completeness: 94.2, accuracy: 90.8, timeliness: 80.0, consistency: 87.2 },
  { key: 'd6', name: '语音详单系统', records: '—', score: 62, completeness: 55.0, accuracy: 70.0, timeliness: 65.0, consistency: 65.0 },
  { key: 'd7', name: '携转资格查询系统', records: '15,440', score: 90, completeness: 97.0, accuracy: 93.5, timeliness: 87.0, consistency: 90.0 },
]

const cols = [
  { title: '数据集', dataIndex: 'name', key: 'name', width: 220 },
  { title: '记录数', dataIndex: 'records', key: 'records', width: 100 },
  { title: '综合评分', key: 'score', width: 180 },
  { title: '完整性', key: 'completeness', width: 90 },
  { title: '准确性', key: 'accuracy', width: 90 },
  { title: '及时性', key: 'timeliness', width: 90 },
  { title: '一致性', key: 'consistency', width: 90 },
]

function scoreColor(s: number) {
  if (s >= 90) return '#52c41a'
  if (s >= 75) return '#fa8c16'
  return '#ff4d4f'
}
</script>

<style scoped>
.ql-tab { display: flex; flex-direction: column; gap: 16px; }
.ql-card {
  background: #fff; border: 1px solid var(--neutral-200); border-radius: 12px;
  padding: 18px 20px; height: 100%;
}
.ql-card__title { font-size: 14px; font-weight: 600; color: var(--neutral-900); margin-bottom: 4px; }
.ql-card__sub { font-size: 12px; color: var(--neutral-500); margin-bottom: 16px; }

.ql-progress { display: flex; justify-content: center; margin: 12px 0 16px; }
.ql-card__row {
  display: flex; justify-content: space-around;
  border-top: 1px solid var(--neutral-100); padding-top: 12px;
}
.ql-card__cell { text-align: center; flex: 1; padding: 0 4px; }
.ql-cell__num { font-size: 16px; font-weight: 700; }
.ql-cell__lbl { font-size: 11px; color: var(--neutral-500); margin-top: 4px; }

.ql-dims { display: flex; flex-direction: column; gap: 12px; }
.ql-dim { display: flex; align-items: center; gap: 12px; }
.ql-dim__name { width: 64px; font-size: 12px; color: var(--neutral-700); flex-shrink: 0; }
.ql-dim__bar { flex: 1; height: 8px; background: var(--neutral-100); border-radius: 4px; overflow: hidden; }
.ql-dim__fill { height: 100%; transition: width 0.3s; }
.ql-dim__score { width: 44px; text-align: right; font-size: 13px; font-weight: 600; }

.ql-alerts { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.ql-alert {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 12px; border-radius: 8px;
  background: var(--neutral-50); border: 1px solid var(--neutral-100);
}
.ql-alert--high { background: #fff5f5; border-color: #ffc9c9; }
.ql-alert--mid { background: #fff8e1; border-color: #ffe082; }
.ql-alert--low { background: #e7f5ff; border-color: #a5d8ff; }
.ql-alert__icon { font-size: 16px; }
.ql-alert__body { flex: 1; }
.ql-alert__title { font-size: 12px; font-weight: 600; color: var(--neutral-800); }
.ql-alert__desc { font-size: 11px; color: var(--neutral-600); margin-top: 2px; line-height: 1.5; }
.ql-alert__time { font-size: 11px; color: var(--neutral-400); flex-shrink: 0; }

.ql-score { display: flex; align-items: center; gap: 8px; }
.ql-score__bar { width: 100px; height: 6px; background: var(--neutral-100); border-radius: 3px; overflow: hidden; }
.ql-score__fill { height: 100%; }
.ql-score__num { font-size: 13px; font-weight: 600; min-width: 28px; }
</style>
