<template>
  <div class="bb-split">
    <!-- Left Panel: List -->
    <div class="bb-left">
      <div class="bb-left__header">
        <h1 class="bb-left__title">宽带装机退单稽核</h1>
        <p class="bb-left__desc">基于本体规则与大模型协同，自动判断退单原因合理性</p>
      </div>

      <!-- KPI row -->
      <div class="bb-kpis" v-if="overview">
        <div class="bb-kpi" v-for="kpi in kpis" :key="kpi.label" :class="kpi.cls">
          <span class="bb-kpi__val">{{ kpi.value }}</span>
          <span class="bb-kpi__lbl">{{ kpi.label }}</span>
        </div>
      </div>

      <!-- Filters -->
      <div class="bb-filters">
        <input v-model="filters.keyword" class="bb-input" placeholder="搜索退单编号/工单号/客户..." @keyup.enter="doSearch" />
        <div class="bb-filters__row">
          <input v-model="filters.start_time" type="date" class="bb-input bb-input--date" />
          <span class="bb-filters__sep">~</span>
          <input v-model="filters.end_time" type="date" class="bb-input bb-input--date" />
        </div>
        <div class="bb-filters__row">
          <select v-model="filters.audit_status" class="bb-select">
            <option value="">全部状态</option>
            <option v-for="s in auditStatuses" :key="s" :value="s">{{ s }}</option>
          </select>
          <select v-model="filters.root_cause_level_one" class="bb-select">
            <option value="">全部根因</option>
            <option v-for="c in causeOptions" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <button class="bb-btn bb-btn--primary bb-btn--block" @click="doSearch">查询</button>
      </div>

      <!-- Table -->
      <div class="bb-list">
        <div
          v-for="row in list" :key="row.churn_id"
          class="bb-list-item"
          :class="{ 'bb-list-item--active': selectedId === row.churn_id }"
          @click="selectOrder(row)"
        >
          <div class="bb-list-item__top">
            <span class="bb-list-item__id">{{ row.churn_id }}</span>
            <span class="bb-status" :class="'bb-status--' + statusClass(row.audit_status)">{{ row.audit_status || '-' }}</span>
          </div>
          <div class="bb-list-item__mid">
            <span>{{ row.customer_name || '-' }}</span>
            <span class="bb-list-item__sep">|</span>
            <span>{{ row.engineer_name || '-' }}</span>
            <span class="bb-list-item__sep">|</span>
            <span>{{ formatTime(row.churn_time) }}</span>
          </div>
          <div class="bb-list-item__bot">
            <span v-if="row.root_cause_level_one" class="bb-cause-tag" :class="'bb-cause-tag--' + causeClass(row.root_cause_level_one)">{{ row.root_cause_level_one }}</span>
            <span v-if="row.root_cause_confidence != null" class="bb-conf-sm">{{ (row.root_cause_confidence * 100).toFixed(0) }}%</span>
            <span class="bb-list-item__phase" v-if="row.churn_phase">{{ row.churn_phase }}</span>
          </div>
          <div class="bb-list-item__actions">
            <button v-if="row.audit_status === '待稽核' || row.audit_status === '失败'" class="bb-link bb-link--analyze" @click.stop="startAnalyze(row)">分析</button>
          </div>
        </div>
        <div v-if="!loading && list.length === 0" class="bb-empty">暂无退单数据</div>
        <div v-if="loading" class="bb-loading"><span class="bb-spinner"></span></div>
      </div>

      <!-- Pagination -->
      <div class="bb-pagination" v-if="total > 0">
        <span class="bb-pagination__info">共 {{ total }} 条</span>
        <div class="bb-pagination__btns">
          <button class="bb-btn bb-btn--sm" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
          <span class="bb-pagination__cur">{{ page }} / {{ totalPages }}</span>
          <button class="bb-btn bb-btn--sm" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
        </div>
      </div>
    </div>

    <!-- Right Panel: Detail / Analysis -->
    <div class="bb-right">
      <template v-if="selected">
        <!-- Order header -->
        <div class="bb-detail-header">
          <div class="bb-detail-header__top">
            <h2 class="bb-detail-header__id">{{ selected.churn_id }}</h2>
            <span class="bb-status" :class="'bb-status--' + statusClass(selected.audit_status)">{{ selected.audit_status }}</span>
            <span v-if="selected.root_cause_level_one" class="bb-cause-tag" :class="'bb-cause-tag--' + causeClass(selected.root_cause_level_one)">{{ selected.root_cause_level_one }}</span>
          </div>
          <div class="bb-detail-header__info">
            <span>客户: {{ detailData?.customer?.customer_name || selected.customer_name || '-' }}</span>
            <span>工单: {{ selected.related_order_no }}</span>
            <span>退单时间: {{ formatTime(selected.churn_time) }}</span>
            <span>工程师: {{ selected.engineer_name || '-' }}</span>
            <span v-if="selected.churn_category_l1">退单原因: {{ selected.churn_category_l1 }}</span>
          </div>
        </div>

        <!-- Tabs -->
        <div class="bb-tabs">
          <button v-for="t in panelTabs" :key="t.key" class="bb-tab" :class="{ 'bb-tab--active': activeTab === t.key }" @click="activeTab = t.key">{{ t.label }}</button>
        </div>

        <!-- Tab: 分析过程 -->
        <div v-if="activeTab === 'process'" class="bb-tab-content">
          <div class="bb-analysis-header">
            <button v-if="!analysisRunning && !analysisDone" class="bb-btn bb-btn--primary" @click="doStartAnalysis">开始分析</button>
            <button v-if="analysisDone" class="bb-btn" @click="doStartAnalysis">重新分析</button>
            <span v-if="analysisRunning" class="bb-analysis-running"><span class="bb-spinner bb-spinner--sm"></span> 分析中...</span>
          </div>
          <div v-if="analysisError" class="bb-analysis-error">{{ analysisError }}</div>

          <!-- Steps -->
          <div class="bb-steps">
            <div v-for="(step, idx) in analysisSteps" :key="step.key" class="bb-step" :class="'bb-step--' + step.state">
              <div class="bb-step__icon">
                <span v-if="step.state === 'pending'" class="bb-step-num">{{ idx + 1 }}</span>
                <span v-else-if="step.state === 'loading'" class="bb-spinner bb-spinner--sm"></span>
                <svg v-else-if="step.state === 'done'" width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 8l3 3 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <svg v-else-if="step.state === 'skip'" width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 8h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                <svg v-else-if="step.state === 'error'" width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              </div>
              <div class="bb-step__connector" v-if="idx < analysisSteps.length - 1"></div>
              <div class="bb-step__body">
                <div class="bb-step__title">{{ step.label }}</div>
                <div class="bb-step__msg" v-if="step.message">{{ step.message }}</div>

                <!-- Evidence cards -->
                <div v-if="step.key === 'recognition' && step.evidences && step.evidences.length > 0" class="bb-ev-cards">
                  <div class="bb-ev-cards__summary">
                    共 {{ ALL_EVIDENCE_CODES.length }} 条证据，命中 <span class="bb-ev-cards__hit-num">{{ step.evidences.filter(e => e.hit).length }}</span> 条
                  </div>
                  <div v-for="ev in mergeAllEvidence(step.evidences)" :key="ev.evidence_code" class="bb-ev-card" :class="ev._active ? (ev.hit ? 'bb-ev-card--hit' : 'bb-ev-card--miss') : 'bb-ev-card--inactive'">
                    <div class="bb-ev-card__badge" :class="ev._active ? (ev.hit ? 'bb-ev-card__badge--hit' : 'bb-ev-card__badge--miss') : 'bb-ev-card__badge--inactive'">{{ ev.evidence_code }}</div>
                    <div class="bb-ev-card__body">
                      <div class="bb-ev-card__top">
                        <span class="bb-ev-card__name">{{ ev.content || ev.evidence_code }}</span>
                        <template v-if="ev._active">
                          <span :class="ev.hit ? 'bb-hit-yes' : 'bb-hit-no'">{{ ev.hit ? '命中' : '未命中' }}</span>
                          <span class="bb-ev-type" :class="'bb-ev-type--' + ev.evidence_type">{{ ev.evidence_type }}</span>
                          <span v-if="ev.confidence != null" class="bb-ev-card__conf">{{ (ev.confidence * 100).toFixed(1) }}%</span>
                        </template>
                        <span v-else class="bb-ev-type" :class="'bb-ev-type--' + ev.evidence_type">{{ ev.evidence_type }}</span>
                      </div>
                      <div class="bb-ev-card__reason" v-if="ev._active && ev.raw_text">{{ ev.raw_text }}</div>
                    </div>
                  </div>
                </div>

                <!-- Attribution streaming -->
                <div v-if="step.key === 'attribution' && step.attributionText" class="bb-step__attribution">
                  <pre class="bb-step__attr-text">{{ step.attributionText }}<span v-if="step.state === 'loading'" class="bb-cursor">|</span></pre>
                </div>

                <!-- Step data tags -->
                <div v-if="step.state === 'done' && step.data" class="bb-step__detail">
                  <template v-if="step.key === 'perception' && (step.data as any).source_types">
                    <span v-for="(cnt, src) in (step.data as any).source_types" :key="src" class="bb-step-tag">{{ src }}: {{ cnt }}</span>
                  </template>
                  <template v-if="step.key === 'recognition'">
                    <span class="bb-step-tag">NLP: {{ (step.data as any).nlp_count }}</span>
                    <span class="bb-step-tag">规则: {{ (step.data as any).rule_count }}</span>
                    <span class="bb-step-tag bb-step-tag--hit">命中: {{ (step.data as any).hit_count }}</span>
                  </template>
                  <template v-if="step.key === 'reasoning' && (step.data as any).logic_hits">
                    <span class="bb-step-tag">规则命中: {{ (step.data as any).logic_hits.length }}</span>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <!-- 原因对比 -->
          <div v-if="analysisDone && attributionData" class="bb-reason-compare">
            <div class="bb-reason-compare__header">
              <span class="bb-reason-compare__title">原因对比</span>
              <span v-if="reasonMatch !== null" class="bb-reason-match" :class="reasonMatch ? 'bb-reason-match--yes' : 'bb-reason-match--no'">
                {{ reasonMatch ? '一致' : '不一致' }}
              </span>
            </div>
            <div class="bb-reason-compare__cards">
              <div class="bb-reason-card bb-reason-card--original">
                <div class="bb-reason-card__label">上报原因</div>
                <div class="bb-reason-card__value">{{ attributionData.churn_category_l1 || '未填写' }}</div>
                <div class="bb-reason-card__sub" v-if="attributionData.churn_category_l2">{{ attributionData.churn_category_l2 }}</div>
                <div class="bb-reason-card__detail" v-if="attributionData.churn_reason_text">{{ attributionData.churn_reason_text }}</div>
              </div>
              <div class="bb-reason-compare__arrow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </div>
              <div class="bb-reason-card" :class="reasonMatch === false ? 'bb-reason-card--mismatch' : 'bb-reason-card--audit'">
                <div class="bb-reason-card__label">稽核原因</div>
                <div class="bb-reason-card__value">{{ attributionData.root_cause_level_one || '未确定' }}</div>
                <div class="bb-reason-card__sub" v-if="attributionData.root_cause_level_two">{{ attributionData.root_cause_level_two }}</div>
                <div class="bb-reason-card__conf" v-if="attributionData.root_cause_confidence != null">置信度 {{ (attributionData.root_cause_confidence * 100).toFixed(1) }}%</div>
              </div>
            </div>
            <div v-if="reasonMatch === false" class="bb-reason-compare__hint">
              上报原因与稽核推理结果不一致，建议关注推荐动作中的回访核实
            </div>
          </div>

          <!-- 推荐动作 -->
          <div v-if="analysisTodos.length > 0" class="bb-todos">
            <div class="bb-todos__title">推荐动作 ({{ analysisTodos.length }})</div>
            <div v-for="todo in analysisTodos" :key="todo.action_id" class="bb-todo-card">
              <div class="bb-todo-card__header">
                <span class="bb-todo-card__name">{{ todo.action_name }}</span>
                <span class="bb-todo-card__priority" :class="'bb-todo-card__priority--' + todo.priority">{{ todo.priority === 'high' ? '高' : todo.priority === 'medium' ? '中' : '低' }}</span>
                <span class="bb-todo-card__status" :class="'bb-todo-card__status--' + todo.status">{{ todoStatusLabel(todo.status) }}</span>
              </div>
              <div class="bb-todo-card__desc">{{ todo.description }}</div>
              <div class="bb-todo-card__meta">
                <div class="bb-todo-card__rule"><span class="bb-todo-card__meta-label">触发规则:</span> {{ todo.trigger_rule }}</div>
                <div class="bb-todo-card__effect"><span class="bb-todo-card__meta-label">预期效果:</span> {{ todo.expected_effect }}</div>
              </div>
              <div v-if="todo.support_evidences?.length" class="bb-todo-card__evidences">
                <span v-for="ev in todo.support_evidences" :key="ev.code" class="bb-todo-card__ev" :class="'bb-todo-card__ev--' + ev.role">{{ ev.code }} {{ ev.name }}</span>
              </div>

              <!-- 动作操作区 -->
              <div class="bb-todo-card__actions">
                <template v-if="todo.status === 'pending_confirm'">
                  <button class="bb-btn bb-btn--primary bb-btn--sm" @click="confirmTodo(todo)">确认</button>
                  <button class="bb-btn bb-btn--sm" @click="rejectTodo(todo)">驳回</button>
                </template>
                <template v-else-if="todo.status === 'pending_feedback'">
                  <!-- resource_check 反馈 -->
                  <div v-if="todo.todo_type === 'resource_check'" class="bb-todo-feedback">
                    <select v-model="todo._feedbackValue" class="bb-select bb-select--sm">
                      <option value="">选择核实结果</option>
                      <option value="有资源">有资源</option>
                      <option value="无资源">无资源</option>
                    </select>
                    <input v-model="todo._feedbackText" class="bb-input bb-input--sm" placeholder="备注说明..." />
                    <button class="bb-btn bb-btn--primary bb-btn--sm" :disabled="!todo._feedbackValue" @click="submitTodoFeedback(todo)">提交反馈</button>
                  </div>
                  <!-- followup_call 反馈 -->
                  <div v-else-if="todo.todo_type === 'followup_call'" class="bb-todo-feedback">
                    <select v-model="todo._feedbackValue" class="bb-select bb-select--sm">
                      <option value="">选择回访结果</option>
                      <option value="确认用户原因">确认用户原因</option>
                      <option value="实际为施工原因">实际为施工原因</option>
                      <option value="实际为资源原因">实际为资源原因</option>
                      <option value="其他">其他</option>
                    </select>
                    <input v-model="todo._feedbackText" class="bb-input bb-input--sm" placeholder="回访记录..." />
                    <button class="bb-btn bb-btn--primary bb-btn--sm" :disabled="!todo._feedbackValue" @click="submitTodoFeedback(todo)">提交反馈</button>
                  </div>
                  <div v-else class="bb-todo-feedback">
                    <span class="bb-todo-card__status bb-todo-card__status--pending_feedback">待反馈</span>
                  </div>
                </template>
                <template v-else-if="todo.status === 'feedback_submitted'">
                  <span class="bb-todo-card__status bb-todo-card__status--feedback_submitted">已反馈</span>
                </template>
              </div>
            </div>

            <!-- 二次归因按钮 -->
            <div v-if="hasCompletedTodos" class="bb-todos__reattr">
              <button class="bb-btn bb-btn--primary" @click="doReAttribute" :disabled="reAttributing">
                <span v-if="reAttributing" class="bb-spinner bb-spinner--sm"></span>
                {{ reAttributing ? '重新归因中...' : '基于反馈重新归因' }}
              </button>
              <span v-if="reAttrResult" class="bb-todos__reattr-msg">{{ reAttrResult }}</span>
            </div>
          </div>

          <div v-if="analysisDone" class="bb-analysis-done">分析完成</div>
        </div>

        <!-- Tab: 本体图谱 -->
        <div v-if="activeTab === 'graph'" class="bb-tab-content">
          <div v-if="graphLoading" class="bb-graph-loading"><span class="bb-spinner"></span> 加载图谱数据...</div>
          <div v-else-if="!graphData || graphData.nodes.length === 0" class="bb-empty">暂无本体图谱数据，请先进行分析</div>
          <template v-else>
            <div class="bb-graph-legend">
              <span v-for="(color, type) in graphNodeColors" :key="type" class="bb-graph-legend__item">
                <span class="bb-graph-legend__dot" :style="{ background: color }"></span>
                {{ graphTypeLabels[type] || type }}
              </span>
            </div>
            <div class="bb-graph-svg-wrap">
              <svg :width="graphWidth" :height="graphHeight" :viewBox="`0 0 ${graphWidth} ${graphHeight}`" class="bb-graph-svg">
                <defs>
                  <marker id="bb-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                    <path d="M0,0 L0,6 L8,3 z" fill="var(--neutral-400)" />
                  </marker>
                </defs>
                <g v-for="(edge, i) in graphEdges" :key="'e'+i">
                  <line :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" stroke="var(--neutral-300)" stroke-width="1.5" marker-end="url(#bb-arrow)" />
                  <text :x="(edge.x1+edge.x2)/2" :y="(edge.y1+edge.y2)/2 - 5" text-anchor="middle" font-size="10" fill="var(--neutral-500)">{{ edge.relation }}</text>
                </g>
                <g v-for="node in graphNodes" :key="node.id">
                  <circle :cx="node.x" :cy="node.y" :r="graphNodeR" :fill="graphNodeColors[node.type] || '#8c8c8c'" opacity="0.9" stroke="var(--neutral-0)" stroke-width="2" />
                  <text :x="node.x" :y="node.y - 3" text-anchor="middle" font-size="10" fill="#fff" font-weight="bold">{{ graphTypeLabels[node.type] || node.type }}</text>
                  <text :x="node.x" :y="node.y + 11" text-anchor="middle" font-size="9" fill="#fff">{{ node.name.length > 8 ? node.name.slice(0, 8) + '...' : node.name }}</text>
                </g>
              </svg>
            </div>
            <div class="bb-graph-info">共 {{ graphData.nodes.length }} 个节点，{{ graphData.edges.length }} 条关系</div>
          </template>
        </div>

      </template>

      <!-- Empty state -->
      <div v-else class="bb-right-empty">
        <div class="bb-right-empty__icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="8" y="12" width="32" height="24" rx="3" stroke="var(--neutral-300)" stroke-width="2"/><path d="M8 18h32" stroke="var(--neutral-300)" stroke-width="2"/><circle cx="14" cy="15" r="1.5" fill="var(--neutral-300)"/><circle cx="19" cy="15" r="1.5" fill="var(--neutral-300)"/></svg>
        </div>
        <p class="bb-right-empty__text">请从左侧列表选择退单工单</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive, watch } from 'vue'
import { broadbandApi } from '../../api/broadband'
import type {
  BroadbandOverview, ChurnListItem, ChurnDetail,
  EvidenceItem, SSEEvent, SSEStepKey, OntologyGraphData, OntologyNode, TodoAction,
} from '../../api/broadband'

// ── List state ──
const loading = ref(true)
const overview = ref<BroadbandOverview | null>(null)
const list = ref<ChurnListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const filters = reactive({ keyword: '', start_time: '', end_time: '', audit_status: '', root_cause_level_one: '' })
const auditStatuses = ['待稽核', '稽核中', '挂起', '完成', '失败']
const causeOptions = ['用户原因', '施工原因', '资源原因', '业务原因']

const ALL_EVIDENCE_CODES: { code: string; name: string; type: 'nlp' | 'rule' }[] = [
  { code: 'E1', name: '用户主动取消意愿', type: 'nlp' }, { code: 'E2', name: '用户搬家/不在本地', type: 'nlp' },
  { code: 'E3', name: '用户装修中', type: 'nlp' }, { code: 'E4', name: '用户选择友商', type: 'nlp' },
  { code: 'E5', name: '用户资费不满', type: 'nlp' }, { code: 'E6', name: '用户要求变更', type: 'nlp' },
  { code: 'E7', name: '联系不上(ASR确认)', type: 'nlp' }, { code: 'E8', name: '实名问题(ASR提及)', type: 'nlp' },
  { code: 'E9', name: '工程师态度问题', type: 'nlp' }, { code: 'E10', name: '工程师乱收费', type: 'nlp' },
  { code: 'E11', name: '施工受阻(物业)', type: 'nlp' }, { code: 'E12', name: '入户线问题', type: 'nlp' },
  { code: 'E13', name: '技术问题无法开通', type: 'nlp' }, { code: 'E14', name: '客户情绪愤怒', type: 'nlp' },
  { code: 'E15', name: '客户情绪焦虑', type: 'nlp' }, { code: 'E16', name: '客户满意', type: 'nlp' },
  { code: 'E17', name: '工程师推诿', type: 'nlp' }, { code: 'E18', name: '多次改约', type: 'nlp' },
  { code: 'E19', name: '资源不足(ASR提及)', type: 'nlp' }, { code: 'E20', name: '建设时间长(ASR提及)', type: 'nlp' },
  { code: 'E21', name: '回访确认用户取消', type: 'nlp' }, { code: 'E22', name: '回访确认施工问题', type: 'nlp' },
  { code: 'E23', name: '回访确认资源问题', type: 'nlp' }, { code: 'E24', name: '回访无法联系', type: 'nlp' },
  { code: 'E25', name: '回访挽回成功', type: 'nlp' },
  { code: 'E26', name: '通话失败≥4次且≥2天', type: 'rule' }, { code: 'E27', name: '派单延迟>24h', type: 'rule' },
  { code: 'E28', name: '工程师90日退单率>15%', type: 'rule' }, { code: 'E29', name: '地址待装库有积压', type: 'rule' },
  { code: 'E30', name: '地址资源状态=不足', type: 'rule' }, { code: 'E31', name: '非无条件受理区域', type: 'rule' },
  { code: 'E32', name: '客户黑灰名单', type: 'rule' }, { code: 'E33', name: '客户欠费', type: 'rule' },
  { code: 'E34', name: '异网通话记录存在', type: 'rule' }, { code: 'E35', name: '人工资源核实结果', type: 'rule' },
  { code: 'E36', name: '竞争对手通话频次高', type: 'rule' }, { code: 'E37', name: '回访补全信息', type: 'rule' },
]

function mergeAllEvidence(extracted: EvidenceItem[]): (EvidenceItem & { _active: boolean })[] {
  const hitMap = new Map(extracted.map(e => [e.evidence_code, e]))
  return ALL_EVIDENCE_CODES.map(def => {
    const matched = hitMap.get(def.code)
    if (matched) return { ...matched, _active: true }
    return { evidence_id: def.code, evidence_code: def.code, content: def.name, evidence_type: def.type, hit: false, confidence: null, raw_text: null, _active: false } as any
  })
}
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

// ── Selection state ──
const selectedId = ref<string | null>(null)
const selected = ref<ChurnListItem | null>(null)
const detailData = ref<ChurnDetail | null>(null)
const activeTab = ref('process')
const autoAnalyze = ref(false)

const panelTabs = [
  { key: 'process', label: '分析过程' },
  { key: 'graph', label: '本体图谱' },
]

// ── Analysis state ──
type StepState = 'pending' | 'loading' | 'done' | 'skip' | 'error'
interface AnalysisStep {
  key: SSEStepKey; label: string; state: StepState
  message?: string; data?: unknown; attributionText?: string
  evidences?: EvidenceItem[]
}
const STEP_ORDER: SSEStepKey[] = ['perception', 'recognition', 'reasoning', 'attribution', 'todo']
const STEP_LABELS: Record<string, string> = {
  perception: '感知 · 数据采集', recognition: '识别 · 证据提取',
  reasoning: '推理 · 逻辑命中', attribution: '归因 · 结论输出',
  todo: '动作 · 推荐生成',
}
function initSteps(): AnalysisStep[] {
  return STEP_ORDER.map(key => ({ key, label: STEP_LABELS[key], state: 'pending' as StepState }))
}
const analysisSteps = ref<AnalysisStep[]>(initSteps())
const analysisRunning = ref(false)
const analysisDone = ref(false)
const analysisError = ref<string | null>(null)
let abortCtrl: AbortController | null = null

// ── Todo / Action state ──
interface TodoWithUI extends TodoAction { _feedbackValue?: string; _feedbackText?: string }
const analysisTodos = ref<TodoWithUI[]>([])
const attributionData = ref<{
  root_cause_code?: string; root_cause_level_one?: string; root_cause_level_two?: string
  root_cause_confidence?: number; churn_reason_text?: string; churn_category_l1?: string; churn_category_l2?: string
} | null>(null)
const reAttributing = ref(false)
const reAttrResult = ref<string | null>(null)
const hasCompletedTodos = computed(() => analysisTodos.value.some(t => t.status === 'feedback_submitted'))
const reasonMatch = computed<boolean | null>(() => {
  if (!attributionData.value) return null
  const reported = attributionData.value.churn_category_l1
  const audited = attributionData.value.root_cause_level_one
  if (!reported || !audited) return null
  return reported === audited
})

function todoStatusLabel(status: string) {
  const m: Record<string, string> = {
    pending_confirm: '待确认', pending_feedback: '待反馈',
    feedback_submitted: '已反馈', rejected: '已驳回',
  }
  return m[status] || status
}

async function confirmTodo(todo: TodoWithUI) {
  if (!selected.value) return
  try {
    await broadbandApi.confirmAction(selected.value.churn_id, todo.action_id)
    todo.status = 'pending_feedback'
  } catch { /* silent */ }
}

async function rejectTodo(todo: TodoWithUI) {
  if (!selected.value) return
  try {
    await broadbandApi.rejectAction(selected.value.churn_id, todo.action_id)
    todo.status = 'rejected'
  } catch { /* silent */ }
}

async function submitTodoFeedback(todo: TodoWithUI) {
  if (!selected.value || !todo._feedbackValue) return
  try {
    await broadbandApi.submitFeedback(selected.value.churn_id, todo.action_id, {
      feedback_type: todo.todo_type,
      feedback_value: todo._feedbackValue,
      feedback_text: todo._feedbackText || '',
    })
    todo.status = 'feedback_submitted'
  } catch { /* silent */ }
}

async function doReAttribute() {
  if (!selected.value) return
  reAttributing.value = true
  reAttrResult.value = null
  try {
    const res = await broadbandApi.reAttribute(selected.value.churn_id)
    reAttrResult.value = res.message
    fetchList()
  } catch (e: any) {
    reAttrResult.value = e?.message || '二次归因失败'
  } finally {
    reAttributing.value = false
  }
}

// ── Graph state ──
const graphData = ref<OntologyGraphData | null>(null)
const graphLoading = ref(false)
const graphNodeColors: Record<string, string> = {
  refund: '#fa5252', order: '#339af0', customer: '#20c997', engineer: '#f59f00',
  address: '#7950f2', channel: '#e64980', product: '#12b886', dispatch: '#868e96', call: '#fd7e14',
}
const graphTypeLabels: Record<string, string> = {
  refund: '退单', order: '工单', customer: '客户', engineer: '工程师',
  address: '地址', channel: '渠道', product: '产品', dispatch: '派单', call: '通话',
}
const graphWidth = 700
const graphHeight = 420
const graphNodeR = 28

// ── Computed: KPIs ──
const kpis = computed(() => {
  const o = overview.value
  if (!o) return []
  const items = [
    { label: '总退单', value: o.total, cls: '' },
    { label: '待稽核', value: o.pending, cls: 'bb-kpi--warning' },
    { label: '稽核中', value: o.analyzing, cls: 'bb-kpi--info' },
    { label: '挂起', value: o.pending_todo, cls: 'bb-kpi--warning' },
    { label: '完成', value: o.completed, cls: 'bb-kpi--success' },
    { label: '失败', value: o.error_count, cls: 'bb-kpi--error' },
  ]
  const always = ['总退单', '待稽核', '完成']
  return [
    ...items.filter(i => always.includes(i.label) || (i.value as number) > 0),
    { label: '准确率', value: ((o.accuracy_rate || 0) * 100).toFixed(1) + '%', cls: 'bb-kpi--accent' },
  ]
})

// ── Computed: Graph layout ──
interface GraphNodePos { id: string; x: number; y: number; type: string; name: string }
const graphNodes = computed<GraphNodePos[]>(() => {
  const nodes = graphData.value?.nodes || []
  if (!nodes.length) return []
  const cx = graphWidth / 2, cy = graphHeight / 2
  const r = Math.min(graphWidth, graphHeight) * 0.35
  return nodes.map((n, i) => {
    const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2
    return { id: n.id, x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle), type: n.type, name: n.name }
  })
})
const graphEdges = computed(() => {
  const nodeMap = new Map(graphNodes.value.map(n => [n.id, n]))
  return (graphData.value?.edges || []).map(e => {
    const src = nodeMap.get(e.source), tgt = nodeMap.get(e.target)
    if (!src || !tgt) return null
    const dx = tgt.x - src.x, dy = tgt.y - src.y
    const dist = Math.sqrt(dx * dx + dy * dy) || 1
    return {
      x1: src.x + (dx / dist) * graphNodeR, y1: src.y + (dy / dist) * graphNodeR,
      x2: tgt.x - (dx / dist) * (graphNodeR + 8), y2: tgt.y - (dy / dist) * (graphNodeR + 8),
      relation: e.relation,
    }
  }).filter(Boolean)
})

// ── Helpers ──
function formatTime(t: string | null) { return t ? t.replace('T', ' ').slice(0, 16) : '-' }
function statusClass(s: string | null) {
  const m: Record<string, string> = { '待稽核': 'pending', '稽核中': 'info', '挂起': 'warning', '完成': 'success', '失败': 'error' }
  return m[s || ''] || 'default'
}
function causeClass(c: string | null) {
  const m: Record<string, string> = { '用户原因': 'user', '施工原因': 'construct', '资源原因': 'resource', '业务原因': 'biz' }
  return m[c || ''] || 'default'
}

// ── Data fetching ──
async function fetchList() {
  loading.value = true
  try {
    const [ov, res] = await Promise.all([
      broadbandApi.overview(),
      broadbandApi.list({ page: page.value, page_size: pageSize, ...filters }),
    ])
    overview.value = ov
    list.value = res.items as ChurnListItem[]
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function doSearch() { page.value = 1; fetchList() }
function goPage(p: number) { page.value = p; fetchList() }

// ── Selection & detail loading ──
async function selectOrder(row: ChurnListItem) {
  selectedId.value = row.churn_id
  selected.value = row
  autoAnalyze.value = false
  activeTab.value = 'process'
  resetAnalysis()
  graphData.value = null
  detailData.value = null
  try {
    detailData.value = await broadbandApi.detail(row.churn_id)
  } catch { /* silent */ }
}

function startAnalyze(row: ChurnListItem) {
  selectedId.value = row.churn_id
  selected.value = row
  autoAnalyze.value = true
  activeTab.value = 'process'
  resetAnalysis()
  graphData.value = null
  detailData.value = null
  broadbandApi.detail(row.churn_id).then(d => { detailData.value = d }).catch(() => {})
  doStartAnalysis()
}


// ── Analysis SSE ──
function resetAnalysis() {
  abortCtrl?.abort()
  abortCtrl = null
  analysisSteps.value = initSteps()
  analysisRunning.value = false
  analysisDone.value = false
  analysisError.value = null
  analysisTodos.value = []
  attributionData.value = null
  reAttrResult.value = null
}

function updateStep(key: SSEStepKey, patch: Partial<AnalysisStep>) {
  analysisSteps.value = analysisSteps.value.map(s => s.key === key ? { ...s, ...patch } : s)
}

function doStartAnalysis() {
  if (!selected.value) return
  resetAnalysis()
  analysisRunning.value = true
  const churnId = selected.value.churn_id

  abortCtrl = broadbandApi.startAnalysis(
    churnId,
    (event: SSEEvent) => handleSSE(event, churnId),
    (err: Error) => {
      analysisError.value = err.message
      analysisRunning.value = false
    },
  )
}

function handleSSE(event: SSEEvent, churnId: string) {
  const { step, status, data, message: msg } = event

  if (step === 'done') {
    analysisRunning.value = false
    analysisDone.value = true
    fetchList()
    loadGraph()
    return
  }
  if (step === 'error') {
    analysisError.value = msg ?? '分析出错'
    analysisRunning.value = false
    return
  }
  if (status === 'start') { updateStep(step, { state: 'loading', message: msg }); return }
  if (status === 'skip') { updateStep(step, { state: 'skip', message: msg }); return }
  if (status === 'complete') {
    if (step === 'recognition') {
      const obj = data as Record<string, unknown> | null
      const evs = Array.isArray(obj?.evidences) ? (obj.evidences as EvidenceItem[]) : []
      updateStep(step, { state: 'done', evidences: evs, data, message: msg })
    } else if (step === 'attribution') {
      const obj = data as Record<string, any> | null
      if (obj) {
        attributionData.value = {
          root_cause_code: obj.root_cause_code,
          root_cause_level_one: obj.root_cause_level_one,
          root_cause_level_two: obj.root_cause_level_two,
          root_cause_confidence: obj.root_cause_confidence,
          churn_reason_text: obj.churn_reason_text,
          churn_category_l1: obj.churn_category_l1,
          churn_category_l2: obj.churn_category_l2,
        }
      }
      analysisSteps.value = analysisSteps.value.map(s =>
        s.key === 'attribution' ? { ...s, state: 'done' } : s
      )
    } else if (step === 'todo') {
      const obj = data as Record<string, any> | null
      if (obj?.todos) {
        analysisTodos.value = (obj.todos as TodoAction[]).map(t => ({ ...t, _feedbackValue: '', _feedbackText: '' }))
      }
      updateStep(step, { state: 'done', data, message: msg })
    } else {
      updateStep(step, { state: 'done', data, message: msg })
    }
    return
  }
  if (step === 'attribution' && status === 'streaming') {
    const token = String(data ?? '')
    analysisSteps.value = analysisSteps.value.map(s =>
      s.key === 'attribution'
        ? { ...s, state: 'loading', attributionText: (s.attributionText ?? '') + token }
        : s
    )
    return
  }
  if (status === 'progress') { updateStep(step, { state: 'loading', message: msg, data }); return }
}

// ── Graph loading ──
async function loadGraph() {
  if (!selected.value) return
  graphLoading.value = true
  try {
    graphData.value = await broadbandApi.ontologyGraph(selected.value.churn_id)
  } catch { graphData.value = null }
  finally { graphLoading.value = false }
}

// ── Tab watchers ──
watch(activeTab, (tab) => {
  if (tab === 'graph' && !graphData.value && !graphLoading.value && selected.value) loadGraph()
})

// Auto-start analysis if autoAnalyze
watch(autoAnalyze, (v) => {
  if (v && !analysisRunning.value && !analysisDone.value) doStartAnalysis()
})

onMounted(fetchList)
onUnmounted(() => { abortCtrl?.abort() })
</script>

<style scoped>
/* ── Layout ── */
.bb-split { display: flex; height: calc(100vh - 56px); overflow: hidden; }
.bb-left { width: 420px; min-width: 420px; display: flex; flex-direction: column; border-right: 1px solid var(--neutral-200); background: var(--neutral-0); overflow: hidden; }
.bb-right { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--neutral-25, #fafafa); }

/* ── Left header ── */
.bb-left__header { padding: 16px 16px 12px; border-bottom: 1px solid var(--neutral-200); }
.bb-left__title { font-size: var(--text-h2-size); font-weight: 700; color: var(--neutral-900); margin: 0; }
.bb-left__desc { font-size: var(--text-code-size); color: var(--neutral-500); margin: 4px 0 0; }

/* ── KPIs ── */
.bb-kpis { display: flex; gap: 6px; padding: 10px 16px; border-bottom: 1px solid var(--neutral-100); }
.bb-kpi { flex: 1; text-align: center; padding: 6px 4px; background: var(--neutral-50); border-radius: var(--radius-md); }
.bb-kpi__val { font-size: var(--text-h2-size); font-weight: 700; color: var(--neutral-900); display: block; }
.bb-kpi__lbl { font-size: var(--text-caption-upper-size); color: var(--neutral-500); }
.bb-kpi--warning .bb-kpi__val { color: var(--kinetic-600); }
.bb-kpi--info .bb-kpi__val { color: var(--status-info); }
.bb-kpi--success .bb-kpi__val { color: var(--status-success); }
.bb-kpi--accent .bb-kpi__val { color: var(--semantic-600); }

/* ── Filters ── */
.bb-filters { padding: 10px 16px; display: flex; flex-direction: column; gap: 6px; border-bottom: 1px solid var(--neutral-100); }
.bb-filters__row { display: flex; gap: 6px; align-items: center; }
.bb-filters__sep { color: var(--neutral-400); font-size: var(--text-code-size); }
.bb-input { height: 32px; padding: 0 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-code-size); background: var(--neutral-0); color: var(--neutral-800); outline: none; width: 100%; }
.bb-input:focus { border-color: var(--semantic-400); }
.bb-input--date { width: auto; flex: 1; }
.bb-select { height: 32px; padding: 0 8px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-code-size); background: var(--neutral-0); color: var(--neutral-800); flex: 1; }

/* ── Buttons ── */
.bb-btn { height: 32px; padding: 0 14px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-code-size); background: var(--neutral-0); color: var(--neutral-700); cursor: pointer; transition: var(--transition-fast); }
.bb-btn:hover { background: var(--neutral-50); }
.bb-btn--primary { background: var(--semantic-500); color: var(--neutral-0); border-color: var(--semantic-500); }
.bb-btn--primary:hover { background: var(--semantic-600); }
.bb-btn--block { width: 100%; }
.bb-btn--sm { height: 28px; padding: 0 10px; font-size: var(--text-caption-size); }
.bb-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── List items ── */
.bb-list { flex: 1; overflow-y: auto; padding: 4px 0; }
.bb-list-item { padding: 10px 16px; cursor: pointer; border-bottom: 1px solid var(--neutral-100); transition: var(--transition-fast); position: relative; }
.bb-list-item:hover { background: var(--neutral-50); }
.bb-list-item--active { background: var(--semantic-50); border-left: 3px solid var(--semantic-500); }
.bb-list-item__top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.bb-list-item__id { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); font-family: var(--font-mono); }
.bb-list-item__mid { font-size: var(--text-code-size); color: var(--neutral-500); display: flex; align-items: center; gap: 4px; }
.bb-list-item__sep { color: var(--neutral-300); }
.bb-list-item__bot { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.bb-list-item__phase { font-size: var(--text-caption-size); color: var(--neutral-500); background: var(--neutral-100); padding: 1px 6px; border-radius: var(--radius-sm); }
.bb-list-item__actions { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); }

/* ── Status / Tags ── */
.bb-status { display: inline-block; padding: 2px 8px; border-radius: var(--radius-full); font-size: var(--text-caption-size); font-weight: 500; }
.bb-status--pending { background: var(--status-warning-bg); color: var(--kinetic-700); }
.bb-status--info { background: var(--status-info-bg, #e7f5ff); color: var(--status-info); }
.bb-status--warning { background: var(--status-warning-bg, #fff3bf); color: var(--kinetic-700); }
.bb-status--error { background: var(--status-error-bg, #ffe3e3); color: var(--status-error); }
.bb-status--success { background: var(--status-success-bg, #e6fcf5); color: var(--status-success); }
.bb-status--default { background: var(--neutral-100); color: var(--neutral-600); }

.bb-cause-tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 500; }
.bb-cause-tag--user { background: var(--status-info-bg); color: var(--status-info); }
.bb-cause-tag--construct { background: var(--kinetic-100); color: var(--kinetic-700); }
.bb-cause-tag--resource { background: var(--status-error-bg); color: var(--kinetic-900); }
.bb-cause-tag--biz { background: var(--status-success-bg); color: var(--dynamic-900); }
.bb-cause-tag--default { background: var(--neutral-100); color: var(--neutral-600); }
.bb-cause-sub { font-size: var(--text-caption-size); color: var(--neutral-500); margin-left: 4px; }
.bb-conf-sm { font-size: var(--text-caption-size); font-weight: 600; color: var(--semantic-600); background: var(--semantic-50); padding: 1px 6px; border-radius: var(--radius-sm); }

/* ── Pagination ── */
.bb-pagination { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; border-top: 1px solid var(--neutral-100); }
.bb-pagination__info { font-size: var(--text-caption-size); color: var(--neutral-500); }
.bb-pagination__btns { display: flex; align-items: center; gap: 8px; }
.bb-pagination__cur { font-size: var(--text-caption-size); color: var(--neutral-600); font-weight: 500; }

/* ── Links ── */
.bb-link { color: var(--semantic-500); text-decoration: none; font-size: var(--text-code-size); font-weight: 500; background: none; border: none; cursor: pointer; }
.bb-link:hover { text-decoration: underline; }
.bb-link--analyze { color: var(--kinetic-500); }

/* ── Empty / Loading ── */
.bb-empty { text-align: center; padding: 40px 16px; color: var(--neutral-400); font-size: var(--text-body-size); }
.bb-loading { text-align: center; padding: 20px; }

/* ── Right panel ── */
.bb-right-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--neutral-400); }
.bb-right-empty__icon { margin-bottom: 12px; }
.bb-right-empty__text { font-size: var(--text-body-size); }

/* ── Detail header ── */
.bb-detail-header { padding: 16px 20px; border-bottom: 1px solid var(--neutral-200); background: var(--neutral-0); }
.bb-detail-header__top { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.bb-detail-header__id { font-size: var(--text-h3-size); font-weight: 700; color: var(--neutral-900); margin: 0; }
.bb-detail-header__info { display: flex; flex-wrap: wrap; gap: 12px; font-size: var(--text-code-size); color: var(--neutral-500); }

/* ── Tabs ── */
.bb-tabs { display: flex; gap: 0; border-bottom: 2px solid var(--neutral-200); background: var(--neutral-0); padding: 0 20px; position: sticky; top: 0; z-index: 1; }
.bb-tab { padding: 10px 18px; font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-500); background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: var(--transition-fast); }
.bb-tab:hover { color: var(--neutral-700); }
.bb-tab--active { color: var(--semantic-600); border-bottom-color: var(--semantic-500); }

/* ── Tab content ── */
.bb-tab-content { flex: 1; overflow-y: auto; padding: 16px 20px; }

/* ── Analysis process ── */
.bb-analysis-header { margin-bottom: 16px; display: flex; align-items: center; gap: 12px; }
.bb-analysis-running { display: flex; align-items: center; gap: 6px; font-size: var(--text-body-size); color: var(--semantic-500); }
.bb-analysis-error { padding: 8px 12px; background: var(--status-error-bg, #ffe3e3); color: var(--status-error); border-radius: var(--radius-md); font-size: var(--text-code-size); margin-bottom: 12px; }
.bb-analysis-done { padding: 8px 12px; background: var(--status-success-bg, #e6fcf5); color: var(--status-success); border-radius: var(--radius-md); font-size: var(--text-code-size); margin-top: 12px; text-align: center; }

/* ── Steps ── */
.bb-steps { display: flex; flex-direction: column; gap: 0; }
.bb-step { display: flex; gap: 12px; position: relative; padding-bottom: 20px; }
.bb-step__icon { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: var(--text-code-size); font-weight: 600; flex-shrink: 0; z-index: 1; }
.bb-step--pending .bb-step__icon { background: var(--neutral-100); color: var(--neutral-500); }
.bb-step--loading .bb-step__icon { background: var(--semantic-50); color: var(--semantic-500); }
.bb-step--done .bb-step__icon { background: var(--status-success-bg, #e6fcf5); color: var(--status-success); }
.bb-step--skip .bb-step__icon { background: var(--neutral-100); color: var(--neutral-400); }
.bb-step--error .bb-step__icon { background: var(--status-error-bg, #ffe3e3); color: var(--status-error); }
.bb-step__connector { position: absolute; left: 13px; top: 28px; bottom: 0; width: 2px; background: var(--neutral-200); }
.bb-step--done .bb-step__connector { background: var(--status-success); }
.bb-step--loading .bb-step__connector { background: var(--semantic-300); }
.bb-step__body { flex: 1; min-width: 0; }
.bb-step__title { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); line-height: 28px; }
.bb-step__msg { font-size: var(--text-code-size); color: var(--neutral-500); margin-top: 4px; }
.bb-step__detail { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.bb-step-tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); background: var(--neutral-100); color: var(--neutral-600); }
.bb-step-tag--hit { background: var(--semantic-50); color: var(--semantic-600); font-weight: 600; }
.bb-step-num { font-size: var(--text-code-size); }
.bb-step__attribution { margin-top: 8px; }
.bb-step__attr-text { font-family: inherit; font-size: var(--text-body-size); color: var(--neutral-800); white-space: pre-wrap; margin: 0; padding: 12px; background: var(--semantic-50); border: 1px solid var(--semantic-200); border-radius: var(--radius-md); }
.bb-cursor { animation: bb-blink 0.8s infinite; color: var(--semantic-500); }
@keyframes bb-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* ── Evidence cards (in analysis) ── */
.bb-ev-cards { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; max-height: 600px; overflow-y: auto; }
.bb-ev-cards__summary { font-size: var(--text-code-size); color: var(--neutral-600); padding: 4px 0; font-weight: 500; position: sticky; top: 0; background: var(--neutral-50); z-index: 1; }
.bb-ev-cards__hit-num { color: var(--dynamic-500); font-weight: 700; }
.bb-ev-card { display: flex; gap: 8px; padding: 8px 10px; border: 1.5px solid var(--neutral-200); border-radius: var(--radius-md); background: var(--neutral-0); }
.bb-ev-card--hit { border-color: var(--dynamic-200); background: var(--status-success-bg); }
.bb-ev-card--miss { border-color: var(--status-error); background: var(--status-error-bg); }
.bb-ev-card__badge { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: var(--text-caption-upper-size); font-weight: 700; color: var(--neutral-0); flex-shrink: 0; }
.bb-ev-card__badge--hit { background: var(--dynamic-500); }
.bb-ev-card__badge--miss { background: var(--status-error); }
.bb-ev-card--inactive { border-color: var(--neutral-200); background: var(--neutral-50); opacity: 0.5; }
.bb-ev-card__badge--inactive { background: var(--neutral-300); }
.bb-ev-card__body { flex: 1; min-width: 0; }
.bb-ev-card__top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.bb-ev-card__name { font-size: var(--text-code-size); font-weight: 500; color: var(--neutral-800); }
.bb-ev-card__conf { font-size: var(--text-caption-size); color: var(--neutral-400); font-family: var(--font-mono); }
.bb-ev-card__reason { font-size: var(--text-caption-size); color: var(--neutral-500); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ── Evidence type tags ── */
.bb-ev-type { display: inline-block; padding: 1px 6px; border-radius: var(--radius-sm); font-size: var(--text-caption-upper-size); font-weight: 500; }
.bb-ev-type--nlp { background: var(--status-info-bg); color: var(--status-info); }
.bb-ev-type--rule { background: var(--neutral-100); color: var(--neutral-600); }
.bb-ev-type--manual { background: var(--kinetic-100); color: var(--kinetic-700); }
.bb-hit-yes { font-size: var(--text-caption-size); color: var(--dynamic-500); font-weight: 500; }
.bb-hit-no { font-size: var(--text-caption-size); color: var(--status-error); font-weight: 500; }

/* ── Graph ── */
.bb-graph-loading { display: flex; align-items: center; gap: 8px; justify-content: center; padding: 40px; color: var(--neutral-500); font-size: var(--text-body-size); }
.bb-graph-legend { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }
.bb-graph-legend__item { display: flex; align-items: center; gap: 4px; font-size: var(--text-caption-size); color: var(--neutral-600); }
.bb-graph-legend__dot { width: 10px; height: 10px; border-radius: 50%; }
.bb-graph-svg-wrap { border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); background: var(--neutral-0); overflow: auto; }
.bb-graph-svg { display: block; width: 100%; min-width: 400px; }
.bb-graph-info { font-size: var(--text-caption-size); color: var(--neutral-400); margin-top: 8px; }

/* ── Spinner ── */
.bb-spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid var(--neutral-200); border-top-color: var(--semantic-500); border-radius: 50%; animation: bb-spin 0.6s linear infinite; }
.bb-spinner--sm { width: 14px; height: 14px; }
@keyframes bb-spin { to { transform: rotate(360deg); } }

/* ── Reason comparison ── */
.bb-reason-compare { margin-top: 16px; padding: 16px; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); }
.bb-reason-compare__header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.bb-reason-compare__title { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.bb-reason-match { display: inline-block; padding: 2px 10px; border-radius: var(--radius-full); font-size: var(--text-caption-size); font-weight: 600; }
.bb-reason-match--yes { background: var(--status-success-bg); color: var(--status-success); }
.bb-reason-match--no { background: var(--status-error-bg); color: var(--status-error); }
.bb-reason-compare__cards { display: flex; align-items: stretch; gap: 12px; }
.bb-reason-compare__arrow { display: flex; align-items: center; color: var(--neutral-400); flex-shrink: 0; }
.bb-reason-compare__hint { margin-top: 10px; padding: 8px 12px; border-radius: var(--radius-sm); background: var(--status-error-bg); color: var(--status-error); font-size: var(--text-code-size); }
.bb-reason-card { flex: 1; padding: 12px; border-radius: var(--radius-md); }
.bb-reason-card--original { background: var(--status-warning-bg); border: 1px solid var(--kinetic-200); }
.bb-reason-card--audit { background: var(--status-success-bg); border: 1px solid var(--dynamic-300); }
.bb-reason-card--mismatch { background: var(--status-error-bg); border: 1px solid var(--status-error); }
.bb-reason-card__label { font-size: var(--text-caption-size); font-weight: 600; color: var(--neutral-500); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.bb-reason-card__value { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-900); }
.bb-reason-card__sub { font-size: var(--text-code-size); color: var(--neutral-600); margin-top: 4px; }
.bb-reason-card__detail { font-size: var(--text-caption-size); color: var(--neutral-500); margin-top: 6px; font-style: italic; line-height: 1.4; }
.bb-reason-card__conf { font-size: var(--text-caption-size); font-weight: 600; color: var(--status-success); margin-top: 4px; }

/* ── Todo / Action cards ── */
.bb-todos { margin-top: 16px; }
.bb-todos__title { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); margin-bottom: 10px; }
.bb-todo-card { padding: 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); background: var(--neutral-0); margin-bottom: 10px; }
.bb-todo-card__header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.bb-todo-card__name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-900); flex: 1; }
.bb-todo-card__priority { font-size: var(--text-caption-upper-size); font-weight: 600; padding: 2px 6px; border-radius: var(--radius-sm); }
.bb-todo-card__priority--high { background: var(--status-error-bg); color: var(--kinetic-900); }
.bb-todo-card__priority--medium { background: var(--kinetic-100); color: var(--kinetic-700); }
.bb-todo-card__priority--low { background: var(--status-info-bg); color: var(--status-info); }
.bb-todo-card__status { font-size: var(--text-caption-upper-size); font-weight: 500; padding: 2px 6px; border-radius: var(--radius-sm); background: var(--neutral-100); color: var(--neutral-600); }
.bb-todo-card__status--executing { background: var(--status-info-bg); color: var(--status-info); }
.bb-todo-card__status--completed { background: var(--status-success-bg); color: var(--dynamic-900); }
.bb-todo-card__status--rejected { background: var(--status-error-bg); color: var(--kinetic-900); }
.bb-todo-card__desc { font-size: var(--text-code-size); color: var(--neutral-600); line-height: 1.5; margin-bottom: 8px; }
.bb-todo-card__meta { font-size: var(--text-caption-size); color: var(--neutral-500); margin-bottom: 8px; }
.bb-todo-card__meta-label { font-weight: 600; color: var(--neutral-600); }
.bb-todo-card__rule, .bb-todo-card__effect { margin-bottom: 2px; }
.bb-todo-card__evidences { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
.bb-todo-card__ev { font-size: var(--text-caption-upper-size); padding: 2px 6px; border-radius: var(--radius-sm); background: var(--neutral-100); color: var(--neutral-600); }
.bb-todo-card__ev--support { background: var(--status-success-bg); color: var(--dynamic-900); }
.bb-todo-card__ev--refute { background: var(--status-error-bg); color: var(--kinetic-900); }
.bb-todo-card__actions { display: flex; align-items: center; gap: 8px; padding-top: 8px; border-top: 1px solid var(--neutral-100); }
.bb-todo-feedback { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.bb-btn--sm { height: 28px; padding: 0 10px; font-size: var(--text-caption-size); }
.bb-select--sm { height: 28px; font-size: var(--text-caption-size); padding: 0 6px; }
.bb-input--sm { height: 28px; font-size: var(--text-caption-size); padding: 0 8px; flex: 1; min-width: 120px; }
.bb-todos__reattr { margin-top: 12px; display: flex; align-items: center; gap: 10px; }
.bb-todos__reattr-msg { font-size: var(--text-code-size); color: var(--status-success); }
</style>
