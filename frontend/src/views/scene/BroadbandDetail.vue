<template>
  <div class="bd-page">
    <div class="bd-breadcrumb">
      <RouterLink to="/scene/broadband" class="bd-breadcrumb__link">宽带退单稽核</RouterLink>
      <span class="bd-breadcrumb__sep">/</span>
      <span class="bd-breadcrumb__cur">退单详情</span>
    </div>

    <PageState :loading="loading" :empty="!loading && !data">
    <template v-if="data">

    <div class="bd-summary">
      <div class="bd-summary__left">
        <h2 class="bd-summary__id">{{ data.churn.churn_id }}</h2>
        <span class="bd-status" :class="'bd-status--' + statusClass(data.churn.audit_status)">{{ data.churn.audit_status }}</span>
        <span v-if="data.churn.root_cause_level_one" class="bd-cause-tag" :class="'bd-cause-tag--' + causeClass(data.churn.root_cause_level_one)">{{ data.churn.root_cause_level_one }}</span>
        <span v-if="data.churn.root_cause_confidence != null" class="bd-conf-inline">{{ (data.churn.root_cause_confidence * 100).toFixed(1) }}%</span>
      </div>
      <div class="bd-summary__actions" v-if="data.churn.audit_status !== '已归档'">
        <button class="bd-btn bd-btn--success" @click="doAudit('archive')">归档</button>
        <button class="bd-btn bd-btn--primary" @click="showOverride = true">覆盖推理</button>
        <button class="bd-btn bd-btn--warning" @click="doAudit('flag_anomaly')">标记异常</button>
      </div>
    </div>

    <!-- Override Modal -->
    <div v-if="showOverride" class="bd-modal-mask" @click.self="showOverride = false">
      <div class="bd-modal">
        <h3 class="bd-modal__title">覆盖推理结论</h3>
        <select v-model="overrideLabel" class="bd-select">
          <option value="">选择根因标签</option>
          <option v-for="c in allCauses" :key="c" :value="c">{{ c }}</option>
        </select>
        <div class="bd-modal__btns">
          <button class="bd-btn" @click="showOverride = false">取消</button>
          <button class="bd-btn bd-btn--primary" @click="doOverride" :disabled="!overrideLabel">确认覆盖</button>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="bd-tabs">
      <button v-for="tab in tabs" :key="tab.key" class="bd-tab" :class="{ 'bd-tab--active': activeTab === tab.key }" @click="activeTab = tab.key">
        {{ tab.label }}
        <span v-if="tab.badge" class="bd-tab__badge">{{ tab.badge }}</span>
      </button>
    </div>

    <!-- PLACEHOLDER_TAB_CONTENT -->

    <!-- Tab: 分析过程 -->
    <div v-if="activeTab === 'analysis'" class="bd-analysis-wrap">
      <div class="bd-analysis-header">
        <button v-if="!analysisRunning && !analysisDone" class="bd-btn bd-btn--primary" @click="startAnalysis">开始分析</button>
        <button v-if="analysisDone" class="bd-btn" @click="startAnalysis">重新分析</button>
        <span v-if="analysisRunning" class="bd-analysis-running">
          <span class="bd-spinner"></span> 分析中...
        </span>
      </div>
      <div v-if="analysisError" class="bd-analysis-error">{{ analysisError }}</div>
      <div class="bd-steps">
        <div v-for="(step, idx) in analysisSteps" :key="step.key" class="bd-step" :class="'bd-step--' + step.state">
          <div class="bd-step__icon">
            <span v-if="step.state === 'pending'" class="bd-step-num">{{ idx + 1 }}</span>
            <span v-else-if="step.state === 'loading'" class="bd-spinner bd-spinner--sm"></span>
            <svg v-else-if="step.state === 'done'" width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 8l3 3 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <svg v-else-if="step.state === 'error'" width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            <span v-else class="bd-step-num">-</span>
          </div>
          <div class="bd-step__connector" v-if="idx < analysisSteps.length - 1"></div>
          <div class="bd-step__body">
            <div class="bd-step__title">{{ step.label }}</div>
            <div class="bd-step__msg" v-if="step.message">{{ step.message }}</div>
            <div v-if="step.key === 'attribution' && step.attributionText" class="bd-step__attribution">
              <pre class="bd-step__attr-text">{{ step.attributionText }}<span v-if="step.state === 'loading'" class="bd-cursor">|</span></pre>
            </div>
            <div v-if="step.state === 'done' && step.data" class="bd-step__detail">
              <template v-if="step.key === 'perception' && (step.data as any).source_types">
                <span v-for="(cnt, src) in (step.data as any).source_types" :key="src" class="bd-step-tag">{{ src }}: {{ cnt }}</span>
              </template>
              <template v-if="step.key === 'recognition'">
                <span class="bd-step-tag">NLP: {{ (step.data as any).nlp_count }}</span>
                <span class="bd-step-tag">规则: {{ (step.data as any).rule_count }}</span>
                <span class="bd-step-tag bd-step-tag--hit">命中: {{ (step.data as any).hit_count }}</span>
              </template>
              <template v-if="step.key === 'reasoning' && (step.data as any).logic_hits">
                <span class="bd-step-tag">规则命中: {{ (step.data as any).logic_hits.length }}</span>
              </template>
            </div>
          </div>
        </div>
      </div>
      <div v-if="analysisDone" class="bd-analysis-done">分析完成</div>
    </div>

    <!-- Tab: 本体图谱 -->
    <div v-if="activeTab === 'graph'" class="bd-graph-wrap">
      <div v-if="graphLoading" class="bd-graph-loading"><span class="bd-spinner"></span> 加载图谱数据...</div>
      <div v-else-if="!graphData || graphData.nodes.length === 0" class="bd-empty">暂无本体图谱数据</div>
      <template v-else>
        <div class="bd-graph-legend">
          <span v-for="(color, type) in graphNodeColors" :key="type" class="bd-graph-legend__item">
            <span class="bd-graph-legend__dot" :style="{ background: color }"></span>
            {{ graphTypeLabels[type] || type }}
          </span>
        </div>
        <div class="bd-graph-svg-wrap">
          <svg :width="graphWidth" :height="graphHeight" :viewBox="`0 0 ${graphWidth} ${graphHeight}`" class="bd-graph-svg">
            <defs>
              <marker id="bd-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L0,6 L8,3 z" fill="var(--neutral-400)" />
              </marker>
            </defs>
            <g v-for="(edge, i) in graphEdges" :key="'e'+i">
              <line :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" stroke="var(--neutral-300)" stroke-width="1.5" marker-end="url(#bd-arrow)" />
              <text :x="(edge.x1+edge.x2)/2" :y="(edge.y1+edge.y2)/2 - 5" text-anchor="middle" font-size="10" fill="var(--neutral-500)">{{ edge.relation }}</text>
            </g>
            <g v-for="node in graphNodes" :key="node.id">
              <circle :cx="node.x" :cy="node.y" :r="graphNodeR" :fill="graphNodeColors[node.type] || '#8c8c8c'" opacity="0.9" stroke="var(--neutral-0)" stroke-width="2" />
              <text :x="node.x" :y="node.y - 3" text-anchor="middle" font-size="10" fill="#fff" font-weight="bold">{{ graphTypeLabels[node.type] || node.type }}</text>
              <text :x="node.x" :y="node.y + 11" text-anchor="middle" font-size="9" fill="#fff">{{ node.name.length > 8 ? node.name.slice(0, 8) + '...' : node.name }}</text>
            </g>
          </svg>
        </div>
        <div class="bd-graph-info">共 {{ graphData.nodes.length }} 个节点，{{ graphData.edges.length }} 条关系</div>
      </template>
    </div>

    <!-- Tab 1: 案件概览 -->
    <div v-if="activeTab === 'overview'" class="bd-body">
      <div class="bd-left">
        <div class="bd-card">
          <div class="bd-card__head">工单信息</div>
          <div class="bd-card__grid" v-if="data.order">
            <div class="bd-field"><span class="bd-field__lbl">工单编号</span><span class="bd-field__val bd-mono">{{ data.order.order_no }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">业务类型</span><span class="bd-field__val">{{ data.order.biz_type }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">产品类型</span><span class="bd-field__val">{{ data.order.product_type }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">产品名称</span><span class="bd-field__val">{{ data.order.product_name }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">受理时间</span><span class="bd-field__val">{{ fmt(data.order.accept_time) }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">工单状态</span><span class="bd-field__val">{{ data.order.order_status }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">装机地址</span><span class="bd-field__val bd-field__val--full">{{ data.order.install_address }}</span></div>
          </div>
        </div>
        <div class="bd-card">
          <div class="bd-card__head">客户信息</div>
          <div class="bd-card__grid" v-if="data.customer">
            <div class="bd-field"><span class="bd-field__lbl">客户姓名</span><span class="bd-field__val">{{ data.customer.customer_name }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">联系电话</span><span class="bd-field__val bd-mono">{{ data.customer.contact_phone }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">客户星级</span><span class="bd-field__val">{{ data.customer.customer_level }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">入网时长</span><span class="bd-field__val">{{ data.customer.network_age }}个月</span></div>
            <div class="bd-field"><span class="bd-field__lbl">历史投诉</span><span class="bd-field__val">{{ data.customer.hist_complaint_count }}次</span></div>
            <div class="bd-field"><span class="bd-field__lbl">历史退单</span><span class="bd-field__val">{{ data.customer.hist_churn_count }}次</span></div>
            <div class="bd-field"><span class="bd-field__lbl">黑灰名单</span><span class="bd-field__val">{{ data.customer.is_blacklist ? '是' : '否' }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">欠费状态</span><span class="bd-field__val">{{ data.customer.arrears_status }}</span></div>
          </div>
        </div>
        <div class="bd-card">
          <div class="bd-card__head">工程师信息</div>
          <div class="bd-card__grid" v-if="data.engineer">
            <div class="bd-field"><span class="bd-field__lbl">姓名</span><span class="bd-field__val">{{ data.engineer.engineer_name }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">班组</span><span class="bd-field__val">{{ data.engineer.team_name }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">技术级别</span><span class="bd-field__val">{{ data.engineer.tech_level }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">90日退单率</span><span class="bd-field__val">{{ pct(data.engineer.churn_rate_90d) }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">准时率</span><span class="bd-field__val">{{ pct(data.engineer.on_time_rate_90d) }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">光衰合格率</span><span class="bd-field__val">{{ pct(data.engineer.optical_qualify_rate) }}</span></div>
          </div>
        </div>
        <div class="bd-card" v-if="data.address">
          <div class="bd-card__head">地址信息</div>
          <div class="bd-card__grid">
            <div class="bd-field"><span class="bd-field__lbl">标准地址</span><span class="bd-field__val bd-field__val--full">{{ data.address.standard_address_name }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">资源状态</span><span class="bd-field__val">{{ data.address.resource_status }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">无条件受理</span><span class="bd-field__val">{{ data.address.is_unconditional_accept ? '是' : '否' }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">历史退单率</span><span class="bd-field__val">{{ pct(data.address.hist_churn_rate) }}</span></div>
          </div>
        </div>
      </div>
      <div class="bd-right">
        <div class="bd-card bd-card--highlight">
          <div class="bd-card__head">稽核结果</div>
          <div class="bd-result">
            <div class="bd-result__row"><span class="bd-result__lbl">退单时间</span><span class="bd-result__val">{{ fmt(data.churn.churn_time) }}</span></div>
            <div class="bd-result__row"><span class="bd-result__lbl">退单原因(原始)</span><span class="bd-result__val">{{ data.churn.churn_reason_text || '-' }}</span></div>
            <div class="bd-result__row"><span class="bd-result__lbl">原始分类</span><span class="bd-result__val">{{ data.churn.churn_category_l1 }} / {{ data.churn.churn_category_l2 }}</span></div>
            <div class="bd-result__divider"></div>
            <div class="bd-result__row"><span class="bd-result__lbl">根因编码</span><span class="bd-result__val bd-mono">{{ data.churn.root_cause_code || '-' }}</span></div>
            <div class="bd-result__row"><span class="bd-result__lbl">根因一级</span><span class="bd-result__val">{{ data.churn.root_cause_level_one || '-' }}</span></div>
            <div class="bd-result__row"><span class="bd-result__lbl">根因二级</span><span class="bd-result__val">{{ data.churn.root_cause_level_two || '-' }}</span></div>
            <div v-if="data.churn.root_cause_confidence != null" class="bd-result__row">
              <span class="bd-result__lbl">置信度</span>
              <span class="bd-result__val">
                <div class="bd-conf-lg">
                  <div class="bd-conf-lg__bar"><div class="bd-conf-lg__fill" :class="confClass(data.churn.root_cause_confidence)" :style="{ width: (data.churn.root_cause_confidence * 100) + '%' }"></div></div>
                  <span class="bd-conf-lg__val">{{ (data.churn.root_cause_confidence * 100).toFixed(1) }}%</span>
                </div>
              </span>
            </div>
          </div>
        </div>
        <!-- PLACEHOLDER_CALLS -->
        <div class="bd-card" v-if="data.call_summary">
          <div class="bd-card__head">通话摘要</div>
          <div class="bd-card__grid">
            <div class="bd-field"><span class="bd-field__lbl">总通话次数</span><span class="bd-field__val">{{ data.call_summary.total_call_count }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">失败次数</span><span class="bd-field__val">{{ data.call_summary.failed_call_count }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">通话天数</span><span class="bd-field__val">{{ data.call_summary.distinct_call_days }}</span></div>
            <div class="bd-field"><span class="bd-field__lbl">有效录音</span><span class="bd-field__val">{{ data.call_summary.has_valid_recording ? '是' : '否' }}</span></div>
          </div>
        </div>
        <div class="bd-card" v-if="data.engineer_calls.length">
          <div class="bd-card__head">工程师通话 ({{ data.engineer_calls.length }})</div>
          <div class="bd-calls">
            <div v-for="c in data.engineer_calls" :key="c.call_id" class="bd-call">
              <div class="bd-call__head">
                <span class="bd-call__time">{{ fmt(c.call_start_time) }}</span>
                <span class="bd-call__dur">{{ c.duration_seconds }}秒</span>
                <span class="bd-call__status" :class="c.connect_status === '已接通' ? 'bd-call__status--ok' : 'bd-call__status--fail'">{{ c.connect_status }}</span>
                <span v-if="c.customer_emotion_tag" class="bd-call__emotion">{{ c.customer_emotion_tag }}</span>
              </div>
              <div class="bd-call__asr" v-if="c.asr_text">{{ c.asr_text }}</div>
            </div>
          </div>
        </div>
        <div class="bd-card" v-if="data.callback_calls.length">
          <div class="bd-card__head">回访通话 ({{ data.callback_calls.length }})</div>
          <div class="bd-calls">
            <div v-for="c in data.callback_calls" :key="c.call_id" class="bd-call">
              <div class="bd-call__head">
                <span class="bd-call__time">{{ fmt(c.call_start_time) }}</span>
                <span v-if="c.duration_seconds" class="bd-call__dur">{{ c.duration_seconds }}秒</span>
                <span v-if="c.callback_target" class="bd-call__purpose">{{ c.callback_target }}</span>
                <span v-if="c.is_mandatory" class="bd-call__mandatory">强制回访</span>
              </div>
              <div class="bd-call__asr" v-if="c.asr_text">{{ c.asr_text }}</div>
              <div class="bd-call__result" v-if="c.callback_result">结果: {{ c.callback_result }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 2: 事实时间线 -->
    <div v-if="activeTab === 'timeline'" class="bd-timeline-wrap">
      <div class="bd-timeline">
        <div v-for="(ev, idx) in timelineEvents" :key="idx" class="bd-tl-item" :class="'bd-tl-item--' + ev.type">
          <div class="bd-tl-dot"></div>
          <div class="bd-tl-line" v-if="idx < timelineEvents.length - 1"></div>
          <div class="bd-tl-content">
            <div class="bd-tl-time">{{ ev.time }}</div>
            <div class="bd-tl-title">{{ ev.title }}</div>
            <div class="bd-tl-desc" v-if="ev.desc">{{ ev.desc }}</div>
            <div class="bd-tl-tags" v-if="ev.tags?.length">
              <span v-for="t in ev.tags" :key="t" class="bd-tl-tag">{{ t }}</span>
            </div>
          </div>
        </div>
        <div v-if="!timelineEvents.length" class="bd-empty">暂无时间线数据</div>
      </div>
    </div>

    <!-- PLACEHOLDER_TAB3456 -->

    <!-- Tab 3: 稽核链路 -->
    <div v-if="activeTab === 'chain'" class="bd-chain-wrap">
      <div v-if="chain" class="bd-pipeline">
        <div class="bd-pipe-step" :class="{ 'bd-pipe-step--done': chain.perception.lf_001_status === 'completed' }">
          <div class="bd-pipe-step__icon">1</div>
          <div class="bd-pipe-step__title">感知</div>
          <div class="bd-pipe-step__sub">数据采集</div>
          <div class="bd-pipe-step__detail">
            <div class="bd-pipe-kv" v-for="(cnt, src) in chain.perception.source_types" :key="src">
              <span class="bd-pipe-kv__k">{{ src }}</span>
              <span class="bd-pipe-kv__v">{{ cnt }}条</span>
            </div>
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">LF-001</span><span class="bd-pipe-kv__v bd-pipe-status" :class="'bd-pipe-status--' + chain.perception.lf_001_status">{{ chain.perception.lf_001_status }}</span></div>
          </div>
        </div>
        <div class="bd-pipe-arrow">→</div>
        <div class="bd-pipe-step" :class="{ 'bd-pipe-step--done': chain.recognition.lf_002_status === 'completed' }">
          <div class="bd-pipe-step__icon">2</div>
          <div class="bd-pipe-step__title">识别</div>
          <div class="bd-pipe-step__sub">证据提取</div>
          <div class="bd-pipe-step__detail">
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">NLP证据</span><span class="bd-pipe-kv__v">{{ chain.recognition.nlp_count }}条</span></div>
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">规则证据</span><span class="bd-pipe-kv__v">{{ chain.recognition.rule_count }}条</span></div>
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">命中数</span><span class="bd-pipe-kv__v bd-pipe-hit">{{ chain.recognition.hit_count }}</span></div>
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">LF-002</span><span class="bd-pipe-kv__v bd-pipe-status" :class="'bd-pipe-status--' + chain.recognition.lf_002_status">{{ chain.recognition.lf_002_status }}</span></div>
          </div>
        </div>
        <div class="bd-pipe-arrow">→</div>
        <div class="bd-pipe-step" :class="{ 'bd-pipe-step--done': chain.reasoning.lf_004_status === 'completed' }">
          <div class="bd-pipe-step__icon">3</div>
          <div class="bd-pipe-step__title">推理</div>
          <div class="bd-pipe-step__sub">假设树 + 置信度</div>
          <div class="bd-pipe-step__detail">
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">逻辑命中</span><span class="bd-pipe-kv__v">{{ chain.reasoning.logic_hits.length }}条</span></div>
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">LF-004</span><span class="bd-pipe-kv__v bd-pipe-status" :class="'bd-pipe-status--' + chain.reasoning.lf_004_status">{{ chain.reasoning.lf_004_status }}</span></div>
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">LF-005</span><span class="bd-pipe-kv__v bd-pipe-status" :class="'bd-pipe-status--' + chain.reasoning.lf_005_status">{{ chain.reasoning.lf_005_status }}</span></div>
          </div>
        </div>
        <div class="bd-pipe-arrow">→</div>
        <div class="bd-pipe-step" :class="{ 'bd-pipe-step--done': chain.output.root_cause_code != null }">
          <div class="bd-pipe-step__icon">4</div>
          <div class="bd-pipe-step__title">输出</div>
          <div class="bd-pipe-step__sub">根因判定</div>
          <div class="bd-pipe-step__detail">
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">根因</span><span class="bd-pipe-kv__v">{{ chain.output.root_cause_level_one || '待定' }} / {{ chain.output.root_cause_level_two || '-' }}</span></div>
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">置信度</span><span class="bd-pipe-kv__v">{{ chain.output.root_cause_confidence != null ? (chain.output.root_cause_confidence * 100).toFixed(1) + '%' : '-' }}</span></div>
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">动作数</span><span class="bd-pipe-kv__v">{{ chain.output.actions.length }}</span></div>
            <div class="bd-pipe-kv"><span class="bd-pipe-kv__k">LF-007</span><span class="bd-pipe-kv__v bd-pipe-status" :class="'bd-pipe-status--' + chain.output.lf_007_status">{{ chain.output.lf_007_status }}</span></div>
          </div>
        </div>
      </div>
      <div v-else class="bd-empty">加载中...</div>
    </div>

    <!-- Tab 4: 证据与规则 -->
    <div v-if="activeTab === 'evidence'" class="bd-evidence-wrap">
      <div class="bd-card">
        <div class="bd-card__head">证据列表 ({{ evidenceList.length }})</div>
        <div class="bd-table-wrap">
          <table class="bd-table">
            <thead><tr><th>编码</th><th>类型</th><th>内容</th><th>来源</th><th>命中</th><th>置信度</th></tr></thead>
            <tbody>
              <tr v-for="e in evidenceList" :key="e.evidence_id" :class="{ 'bd-table__row--hit': e.hit }">
                <td class="bd-mono">{{ e.evidence_code }}</td>
                <td><span class="bd-ev-type" :class="'bd-ev-type--' + e.evidence_type">{{ e.evidence_type }}</span></td>
                <td>{{ e.content }}</td>
                <td>{{ e.source_type || '-' }}</td>
                <td><span :class="e.hit ? 'bd-hit-yes' : 'bd-hit-no'">{{ e.hit ? '命中' : '未命中' }}</span></td>
                <td>{{ e.confidence != null ? (e.confidence * 100).toFixed(1) + '%' : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="bd-card" style="margin-top: 12px;">
        <div class="bd-card__head">逻辑函数命中 ({{ logicHits.length }})</div>
        <div class="bd-table-wrap">
          <table class="bd-table">
            <thead><tr><th>函数ID</th><th>函数名</th><th>规则表达式</th><th>结果</th><th>置信度增量</th><th>关联证据</th></tr></thead>
            <tbody>
              <tr v-for="lh in logicHits" :key="lh.hit_id" :class="{ 'bd-table__row--hit': lh.hit_result === 'hit' }">
                <td class="bd-mono">{{ lh.logic_function_id }}</td>
                <td>{{ lh.logic_function_name }}</td>
                <td class="bd-mono" style="font-size:11px;">{{ lh.rule_expression }}</td>
                <td><span class="bd-lh-result" :class="'bd-lh-result--' + lh.hit_result">{{ lh.hit_result }}</span></td>
                <td>{{ lh.confidence_delta > 0 ? '+' : '' }}{{ (lh.confidence_delta * 100).toFixed(1) }}%</td>
                <td class="bd-mono" style="font-size:11px;">{{ lh.evidence_id || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- PLACEHOLDER_TAB56 -->

    <!-- Tab 5: 稽核动作 -->
    <div v-if="activeTab === 'actions'" class="bd-actions-wrap">
      <div v-for="a in actionsList" :key="a.action_id" class="bd-act-card">
        <div class="bd-act-card__header">
          <span class="bd-act-card__code bd-mono">{{ a.action_type_code }}</span>
          <span class="bd-act-card__name">{{ a.action_name }}</span>
          <span class="bd-act-card__priority" :class="'bd-act-card__priority--' + a.priority">{{ a.priority }}</span>
          <span class="bd-act-card__status" :class="'bd-act-card__status--' + a.status">{{ actionStatusLabel(a.status) }}</span>
        </div>
        <div class="bd-act-card__desc" v-if="a.description">{{ a.description }}</div>
        <div class="bd-act-card__meta">
          <span>指派: {{ a.assignee || '-' }}</span>
          <span>创建: {{ fmt(a.created_at) }}</span>
          <span v-if="a.approved_by">审批: {{ a.approved_by }} @ {{ fmt(a.approved_at) }}</span>
          <span v-if="a.rejected_by">驳回: {{ a.rejected_by }} — {{ a.reject_reason }}</span>
        </div>
        <div v-if="a.status === 'pending_approval'" class="bd-act-card__btns">
          <button class="bd-btn bd-btn--success bd-btn--sm" @click="handleApprove(a)">审批通过</button>
          <button class="bd-btn bd-btn--warning bd-btn--sm" @click="handleReject(a)">驳回</button>
        </div>
      </div>
      <div v-if="!actionsList.length" class="bd-empty">暂无稽核动作</div>
    </div>

    <!-- Tab 6: 追溯日志 -->
    <div v-if="activeTab === 'trail'" class="bd-trail-wrap">
      <div v-for="t in trailList" :key="t.trail_id" class="bd-trail-item">
        <div class="bd-trail-item__time">{{ fmt(t.created_at) }}</div>
        <div class="bd-trail-item__type">
          <span class="bd-trail-type-tag" :class="'bd-trail-type-tag--' + t.event_type">{{ trailTypeLabel(t.event_type) }}</span>
        </div>
        <div class="bd-trail-item__detail">{{ t.event_detail }}</div>
        <div class="bd-trail-item__op">{{ t.operator }}</div>
      </div>
      <div v-if="!trailList.length" class="bd-empty">暂无追溯记录</div>
    </div>

    <!-- Tab: 语音质检 -->
    <div v-if="activeTab === 'voice'" class="bd-voice-wrap">
      <div class="bd-voice-header">
        <span class="bd-voice-hint">基于通话 ASR 文本，AI 自动检测工程师话术合规性</span>
        <div class="bd-voice-actions">
          <button class="bd-btn bd-btn--primary" @click="runVoiceAudit" :disabled="voiceAuditing">
            <span v-if="voiceAuditing" class="bd-spinner bd-spinner--sm"></span>
            {{ voiceAuditing ? '质检中...' : '开始质检' }}
          </button>
        </div>
      </div>

      <!-- 补录文本区 -->
      <div class="bd-voice-extra">
        <div class="bd-voice-extra__label">补录通话文本（可选）</div>
        <textarea v-model="extraAsrText" class="bd-voice-textarea" placeholder="粘贴工程师与客户的通话文本，或上传 ASR 转写结果..."></textarea>
      </div>

      <!-- 通话列表 -->
      <div class="bd-voice-calls">
        <div v-for="call in voiceCalls" :key="call.call_id" class="bd-voice-call">
          <div class="bd-voice-call__meta">
            <span class="bd-voice-call__type" :class="'bd-voice-call__type--' + call.call_type">
              {{ call.call_type === 'engineer' ? '工程师通话' : '回访通话' }}
            </span>
            <span class="bd-voice-call__time">{{ call.call_time }}</span>
            <span class="bd-voice-call__eng" v-if="call.engineer_name">{{ call.engineer_name }}</span>
            <span v-if="call.result" class="bd-voice-badge" :class="'bd-voice-badge--' + call.result.overall">
              {{ { pass: '合规', fail: '违规', warning: '警告', error: '错误' }[call.result.overall] }}
              <template v-if="call.result.score != null"> · {{ call.result.score }}分</template>
            </span>
          </div>
          <div class="bd-voice-call__asr">{{ call.asr_text || '（无ASR文本）' }}</div>
          <!-- 质检结果 -->
          <div v-if="call.result && !call.result.skipped && !call.result.error" class="bd-voice-result">
            <div class="bd-voice-result__summary">{{ call.result.summary }}</div>
            <div class="bd-voice-dims">
              <div v-for="d in call.result.dimensions" :key="d.name" class="bd-voice-dim" :class="'bd-voice-dim--' + d.result">
                <span class="bd-voice-dim__icon">
                  <svg v-if="d.result === 'pass'" width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M4 8l3 3 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  <svg v-else-if="d.result === 'fail'" width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                  <span v-else>—</span>
                </span>
                <span class="bd-voice-dim__name">{{ d.name }}</span>
                <span class="bd-voice-dim__comment">{{ d.comment }}</span>
              </div>
            </div>
            <div v-if="call.result.risk_flags?.length" class="bd-voice-risks">
              <span class="bd-voice-risk-label">风险标记：</span>
              <span v-for="f in call.result.risk_flags" :key="f" class="bd-voice-risk-tag">{{ f }}</span>
            </div>
          </div>
          <div v-if="call.result?.error" class="bd-voice-error">质检失败：{{ call.result.error }}</div>
        </div>
        <div v-if="!voiceCalls.length" class="bd-empty">该案件暂无通话记录</div>
      </div>
    </div>

    </template>
    </PageState>
  </div>
</template>

<!-- PLACEHOLDER_SCRIPT -->

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import PageState from '../../components/common/PageState.vue'
import { broadbandApi } from '../../api/broadband'
import type { ChurnDetail, AuditChain, EvidenceItem, LogicHit, AuditAction, AuditTrailItem, SSEEvent, SSEStepKey, OntologyGraphData, OntologyNode, VoiceAuditResult } from '../../api/broadband'

const route = useRoute()
const loading = ref(true)
const data = ref<ChurnDetail | null>(null)
const chain = ref<AuditChain | null>(null)
const evidenceList = ref<EvidenceItem[]>([])
const logicHits = ref<LogicHit[]>([])
const actionsList = ref<AuditAction[]>([])
const trailList = ref<AuditTrailItem[]>([])
const showOverride = ref(false)
const overrideLabel = ref('')
const activeTab = ref('overview')

// ── 分析过程 state ──
type StepState = 'pending' | 'loading' | 'done' | 'skip' | 'error'
interface AnalysisStep { key: SSEStepKey; label: string; state: StepState; message?: string; data?: unknown; attributionText?: string }
const STEP_ORDER: SSEStepKey[] = ['perception', 'recognition', 'reasoning', 'attribution']
const STEP_LABELS: Record<string, string> = { perception: '感知 · 数据采集', recognition: '识别 · 证据提取', reasoning: '推理 · 逻辑命中', attribution: '归因 · 结论输出' }
function initSteps(): AnalysisStep[] { return STEP_ORDER.map(key => ({ key, label: STEP_LABELS[key], state: 'pending' as StepState })) }
const analysisSteps = ref<AnalysisStep[]>(initSteps())
const analysisRunning = ref(false)
const analysisDone = ref(false)
const analysisError = ref<string | null>(null)
let abortCtrl: AbortController | null = null

// ── 本体图谱 state ──
const graphData = ref<OntologyGraphData | null>(null)
const graphLoading = ref(false)

const allCauses = [
  'R1-所在区域无资源', 'R2-建设时间长不愿等', 'R3-非无条件装机区域',
  'R4-待装无建设计划', 'R5-资源不足', 'R6-指定受理渠道',
  'S1-线路不通', 'S2-施工受阻', 'S3-工程师问题',
  'U1-用户取消', 'U2-无法联系', 'U3-已报装其他', 'U4-资费问题',
  'B1-用户办理限制', 'B2-重复单', 'B3-没有申请', 'B4-受理信息错误',
]

const tabs = computed(() => [
  { key: 'overview', label: '案件概览' },
  { key: 'analysis', label: '分析过程' },
  { key: 'graph', label: '本体图谱' },
  { key: 'timeline', label: '事实时间线', badge: timelineEvents.value.length || undefined },
  { key: 'chain', label: '稽核链路' },
  { key: 'evidence', label: '证据与规则', badge: evidenceList.value.filter(e => e.hit).length || undefined },
  { key: 'actions', label: '稽核动作', badge: actionsList.value.filter(a => a.status === 'pending_approval').length || undefined },
  { key: 'trail', label: '追溯日志', badge: trailList.value.length || undefined },
  { key: 'voice', label: '语音质检' },
])

const timelineEvents = computed(() => {
  if (!data.value) return []
  const events: { time: string; title: string; desc?: string; type: string; tags?: string[] }[] = []
  const d = data.value
  if (d.order?.accept_time) events.push({ time: fmt(d.order.accept_time), title: '工单受理', desc: `${d.order.biz_type} / ${d.order.product_name}`, type: 'order', tags: [d.order.order_status] })
  if (d.dispatch?.dispatch_time) events.push({ time: fmt(d.dispatch.dispatch_time), title: '派单', desc: `工程师: ${d.engineer?.engineer_name || '-'}`, type: 'dispatch' })
  if (d.dispatch?.book_time) events.push({ time: fmt(d.dispatch.book_time), title: '预约上门', type: 'dispatch' })
  if (d.dispatch?.arrive_time) events.push({ time: fmt(d.dispatch.arrive_time), title: '工程师到达', desc: d.dispatch.late_duration_minutes > 0 ? `延误${d.dispatch.late_duration_minutes}分钟` : '准时', type: 'dispatch' })
  for (const c of d.engineer_calls) {
    events.push({ time: fmt(c.call_start_time), title: '工程师通话', desc: c.asr_text?.slice(0, 60) || '', type: 'call', tags: [c.connect_status, c.customer_emotion_tag].filter(Boolean) })
  }
  for (const c of d.callback_calls) {
    events.push({ time: fmt(c.call_start_time), title: '回访通话', desc: c.asr_text?.slice(0, 60) || c.callback_result || '', type: 'callback', tags: [c.callback_target, c.is_mandatory ? '强制回访' : ''].filter(Boolean) })
  }
  for (const c of d.competitor_calls) {
    events.push({ time: fmt(c.call_time), title: '异网通话', desc: c.competitor_type, type: 'competitor' })
  }
  if (d.churn?.churn_time) events.push({ time: fmt(d.churn.churn_time), title: '退单', desc: d.churn.churn_reason_text, type: 'churn', tags: [d.churn.churn_category_l1, d.churn.churn_category_l2].filter(Boolean) })
  events.sort((a, b) => a.time.localeCompare(b.time))
  return events
})

function fmt(t: string | null) { return t ? t.replace('T', ' ').slice(0, 16) : '-' }
function pct(v: number | null) { return v != null ? (v * 100).toFixed(1) + '%' : '-' }
function statusClass(s: string | null) {
  const m: Record<string, string> = { '待稽核': 'pending', '推理中': 'info', '待补全回访': 'warning', '强制回访待核实': 'warning', '待人工审核': 'error', '已归档': 'success' }
  return m[s || ''] || 'default'
}
function causeClass(c: string | null) {
  const m: Record<string, string> = { '用户原因': 'user', '施工原因': 'construct', '资源原因': 'resource', '业务原因': 'biz' }
  return m[c || ''] || 'default'
}
function confClass(v: number) {
  if (v >= 0.85) return 'bd-conf-lg__fill--high'
  if (v >= 0.6) return 'bd-conf-lg__fill--mid'
  return 'bd-conf-lg__fill--low'
}
function actionStatusLabel(s: string) {
  const m: Record<string, string> = { pending_approval: '待审批', approved: '已审批', rejected: '已驳回', executing: '执行中', completed: '已完成', failed: '失败' }
  return m[s] || s
}
function trailTypeLabel(t: string) {
  const m: Record<string, string> = { evidence_extracted: '证据提取', logic_hit: '逻辑命中', action_created: '动作创建', action_approved: '动作审批', action_rejected: '动作驳回', action_executed: '动作执行', status_changed: '状态变更', manual_override: '人工覆盖' }
  return m[t] || t
}

// PLACEHOLDER_SCRIPT_ACTIONS

function updateStep(key: SSEStepKey, patch: Partial<AnalysisStep>) {
  analysisSteps.value = analysisSteps.value.map(s => s.key === key ? { ...s, ...patch } : s)
}

function handleSSEEvent(event: SSEEvent) {
  const { step, status, data: evData, message } = event
  if (step === 'done') { analysisRunning.value = false; analysisDone.value = true; return }
  if (step === 'error') { analysisError.value = message ?? '分析出错'; analysisRunning.value = false; return }
  if (status === 'start') { updateStep(step, { state: 'loading', message }); return }
  if (status === 'skip') { updateStep(step, { state: 'skip', message }); return }
  if (status === 'progress') { updateStep(step, { message }); return }
  if (step === 'attribution' && status === 'streaming') {
    const token = String(evData ?? '')
    analysisSteps.value = analysisSteps.value.map(s =>
      s.key === 'attribution' ? { ...s, state: 'loading', attributionText: (s.attributionText ?? '') + token } : s
    )
    return
  }
  if (status === 'complete') {
    updateStep(step, { state: 'done', message, data: evData })
    return
  }
}

function startAnalysis() {
  const id = route.params.id as string
  analysisRunning.value = true
  analysisDone.value = false
  analysisError.value = null
  analysisSteps.value = initSteps()
  abortCtrl?.abort()
  abortCtrl = broadbandApi.startAnalysis(id, handleSSEEvent, (err) => {
    analysisError.value = err.message
    analysisRunning.value = false
  })
}

async function loadGraph() {
  const id = route.params.id as string
  graphLoading.value = true
  try { graphData.value = await broadbandApi.ontologyGraph(id) }
  finally { graphLoading.value = false }
}

import { watch } from 'vue'
watch(activeTab, (tab) => {
  if (tab === 'graph' && !graphData.value && !graphLoading.value) loadGraph()
})

const graphNodeColors: Record<string, string> = {
  refund: '#fa5252', order: '#339af0', customer: '#20c997', engineer: '#f59f00',
  address: '#7950f2', channel: '#e64980', product: '#12b886', dispatch: '#868e96', call: '#fd7e14',
}
const graphTypeLabels: Record<string, string> = {
  refund: '退单', order: '工单', customer: '客户', engineer: '工程师',
  address: '地址', channel: '渠道', product: '产品', dispatch: '派单', call: '通话',
}
const graphWidth = 800
const graphHeight = 500
const graphNodeR = 30

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

async function doAudit(action: string) {
  const id = route.params.id as string
  await broadbandApi.audit(id, { action })
  data.value = await broadbandApi.detail(id)
}
async function doOverride() {
  const id = route.params.id as string
  await broadbandApi.audit(id, { action: 'override', override_label: overrideLabel.value })
  showOverride.value = false
  data.value = await broadbandApi.detail(id)
}
async function handleApprove(a: AuditAction) {
  const id = route.params.id as string
  await broadbandApi.approveAction(id, a.action_id)
  const res = await broadbandApi.actions(id)
  actionsList.value = res.items
}
async function handleReject(a: AuditAction) {
  const reason = prompt('请输入驳回原因:')
  if (reason === null) return
  const id = route.params.id as string
  await broadbandApi.rejectAction(id, a.action_id, reason)
  const res = await broadbandApi.actions(id)
  actionsList.value = res.items
}

onMounted(async () => {
  loading.value = true
  try {
    const id = route.params.id as string
    const [detail, chainData, evData, lhData, actData, trData] = await Promise.all([
      broadbandApi.detail(id),
      broadbandApi.chain(id),
      broadbandApi.evidence(id),
      broadbandApi.logicHits(id),
      broadbandApi.actions(id),
      broadbandApi.trail(id),
    ])
    data.value = detail
    chain.value = chainData
    evidenceList.value = evData.items
    logicHits.value = lhData.items
    actionsList.value = actData.items
    trailList.value = trData.items
  } finally {
    loading.value = false
  }
  if (route.query.tab === 'analysis') {
    activeTab.value = 'analysis'
    startAnalysis()
  }
})

// ── 语音质检 ──────────────────────────────────────────────────
interface VoiceCall {
  call_id: string
  call_type: 'engineer' | 'callback'
  call_time: string
  asr_text: string
  engineer_name?: string
  result?: VoiceAuditResult
}

const voiceAuditing = ref(false)
const extraAsrText = ref('')

const voiceCalls = computed<VoiceCall[]>(() => {
  if (!data.value) return []
  const calls: VoiceCall[] = []
  for (const c of data.value.engineer_calls || []) {
    calls.push({
      call_id: c.call_id || String(Math.random()),
      call_type: 'engineer',
      call_time: fmt(c.call_start_time),
      asr_text: c.asr_text || '',
      engineer_name: data.value.engineer?.engineer_name,
      result: voiceResults.value[c.call_id],
    })
  }
  for (const c of data.value.callback_calls || []) {
    calls.push({
      call_id: c.call_id || String(Math.random()),
      call_type: 'callback',
      call_time: fmt(c.call_start_time),
      asr_text: c.asr_text || '',
      result: voiceResults.value[c.call_id],
    })
  }
  if (extraAsrText.value.trim()) {
    calls.push({
      call_id: 'extra-manual',
      call_type: 'engineer',
      call_time: '补录',
      asr_text: extraAsrText.value.trim(),
      result: voiceResults.value['extra-manual'],
    })
  }
  return calls
})

const voiceResults = ref<Record<string, VoiceAuditResult>>({})

async function runVoiceAudit() {
  const id = route.params.id as string
  const calls = voiceCalls.value
    .filter(c => c.asr_text.trim())
    .map(c => ({ call_id: c.call_id, call_type: c.call_type, asr_text: c.asr_text, engineer_name: c.engineer_name }))
  if (!calls.length) { alert('没有可质检的通话文本'); return }
  voiceAuditing.value = true
  try {
    const res = await broadbandApi.voiceAudit(id, calls)
    for (const r of res.results) {
      voiceResults.value[r.call_id] = r
    }
  } finally {
    voiceAuditing.value = false
  }
}</script>

<!-- PLACEHOLDER_STYLE -->

<style scoped>
.bd-page { padding: 24px; }
.bd-breadcrumb { display: flex; align-items: center; gap: 6px; margin-bottom: 16px; font-size: 13px; }
.bd-breadcrumb__link { color: var(--semantic-500); text-decoration: none; }
.bd-breadcrumb__link:hover { text-decoration: underline; }
.bd-breadcrumb__sep { color: var(--neutral-400); }
.bd-breadcrumb__cur { color: var(--neutral-600); }

.bd-summary { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.bd-summary__left { display: flex; align-items: center; gap: 12px; }
.bd-summary__id { font-size: 20px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.bd-summary__actions { display: flex; gap: 8px; }
.bd-conf-inline { font-size: 13px; font-weight: 600; color: var(--semantic-600); background: var(--semantic-50); padding: 2px 8px; border-radius: var(--radius-sm); }

.bd-btn { height: 34px; padding: 0 14px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: 13px; background: var(--neutral-0); color: var(--neutral-700); cursor: pointer; transition: var(--transition-fast); }
.bd-btn:hover { background: var(--neutral-50); }
.bd-btn--primary { background: var(--semantic-500); color: #fff; border-color: var(--semantic-500); }
.bd-btn--primary:hover { background: var(--semantic-600); }
.bd-btn--success { background: var(--status-success); color: #fff; border-color: var(--status-success); }
.bd-btn--warning { background: var(--kinetic-500); color: #fff; border-color: var(--kinetic-500); }
.bd-btn--sm { height: 28px; padding: 0 10px; font-size: 12px; }
.bd-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.bd-status { display: inline-block; padding: 3px 10px; border-radius: var(--radius-full); font-size: 12px; font-weight: 500; }
.bd-status--pending { background: #fff8e1; color: #e67700; }
.bd-status--info { background: var(--status-info-bg); color: var(--status-info); }
.bd-status--warning { background: var(--status-warning-bg); color: #e67700; }
.bd-status--error { background: var(--status-error-bg); color: var(--status-error); }
.bd-status--success { background: var(--status-success-bg); color: var(--status-success); }
.bd-status--default { background: var(--neutral-100); color: var(--neutral-600); }

.bd-cause-tag { display: inline-block; padding: 3px 10px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; }
.bd-cause-tag--user { background: #e7f5ff; color: #1971c2; }
.bd-cause-tag--construct { background: #fff3bf; color: #e67700; }
.bd-cause-tag--resource { background: #ffe3e3; color: #c92a2a; }
.bd-cause-tag--biz { background: #e6fcf5; color: #087f5b; }
.bd-cause-tag--default { background: var(--neutral-100); color: var(--neutral-600); }

/* Tabs */
.bd-tabs { display: flex; gap: 0; border-bottom: 2px solid var(--neutral-200); margin-bottom: 16px; }
.bd-tab { padding: 10px 18px; font-size: 13px; font-weight: 500; color: var(--neutral-500); background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: var(--transition-fast); display: flex; align-items: center; gap: 6px; }
.bd-tab:hover { color: var(--neutral-700); }
.bd-tab--active { color: var(--semantic-600); border-bottom-color: var(--semantic-500); }
.bd-tab__badge { font-size: 10px; font-weight: 600; background: var(--semantic-500); color: #fff; padding: 1px 6px; border-radius: var(--radius-full); min-width: 18px; text-align: center; }

/* PLACEHOLDER_STYLE2 */

/* Overview layout */
.bd-body { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
.bd-left, .bd-right { display: flex; flex-direction: column; gap: 12px; }
.bd-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); overflow: hidden; }
.bd-card--highlight { border-color: var(--semantic-200); }
.bd-card__head { display: flex; align-items: center; gap: 8px; padding: 12px 16px; font-size: 13px; font-weight: 600; color: var(--neutral-800); background: var(--neutral-50); border-bottom: 1px solid var(--neutral-200); }
.bd-card__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.bd-field { padding: 10px 16px; border-bottom: 1px solid var(--neutral-50); }
.bd-field__lbl { display: block; font-size: 11px; color: var(--neutral-400); margin-bottom: 2px; }
.bd-field__val { display: block; font-size: 13px; color: var(--neutral-800); }
.bd-field__val--full { grid-column: 1 / -1; }
.bd-mono { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; }

.bd-result { padding: 12px 16px; }
.bd-result__row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; }
.bd-result__lbl { color: var(--neutral-500); }
.bd-result__val { color: var(--neutral-800); font-weight: 500; text-align: right; max-width: 60%; }
.bd-result__divider { height: 1px; background: var(--neutral-100); margin: 8px 0; }

.bd-conf-lg { display: flex; align-items: center; gap: 8px; }
.bd-conf-lg__bar { width: 100px; height: 8px; background: var(--neutral-100); border-radius: 4px; overflow: hidden; }
.bd-conf-lg__fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
.bd-conf-lg__fill--high { background: var(--status-success); }
.bd-conf-lg__fill--mid { background: var(--kinetic-500); }
.bd-conf-lg__fill--low { background: var(--status-error); }
.bd-conf-lg__val { font-size: 13px; font-weight: 600; color: var(--neutral-700); }

.bd-calls { max-height: 400px; overflow-y: auto; }
.bd-call { padding: 10px 16px; border-bottom: 1px solid var(--neutral-50); }
.bd-call:last-child { border-bottom: none; }
.bd-call__head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.bd-call__time { font-size: 12px; color: var(--neutral-500); }
.bd-call__dur { font-size: 11px; color: var(--neutral-400); }
.bd-call__status { font-size: 11px; padding: 1px 6px; border-radius: var(--radius-sm); }
.bd-call__status--ok { background: var(--status-success-bg); color: var(--status-success); }
.bd-call__status--fail { background: var(--status-error-bg); color: var(--status-error); }
.bd-call__emotion { font-size: 11px; padding: 1px 6px; border-radius: var(--radius-sm); background: var(--neutral-100); color: var(--neutral-600); }
.bd-call__purpose { font-size: 11px; padding: 1px 6px; border-radius: var(--radius-sm); background: var(--semantic-50); color: var(--semantic-600); }
.bd-call__mandatory { font-size: 11px; padding: 1px 6px; border-radius: var(--radius-sm); background: var(--status-error-bg); color: var(--status-error); font-weight: 500; }
.bd-call__asr { margin-top: 6px; font-size: 13px; color: var(--neutral-700); line-height: 1.5; padding: 8px 12px; background: var(--neutral-50); border-radius: var(--radius-md); }
.bd-call__result { margin-top: 4px; font-size: 12px; color: var(--semantic-600); font-weight: 500; }

/* PLACEHOLDER_STYLE3 */

/* Timeline */
.bd-timeline-wrap { max-width: 700px; }
.bd-timeline { position: relative; padding-left: 24px; }
.bd-tl-item { position: relative; padding-bottom: 24px; }
.bd-tl-dot { position: absolute; left: -24px; top: 4px; width: 12px; height: 12px; border-radius: 50%; background: var(--neutral-300); border: 2px solid var(--neutral-0); z-index: 1; }
.bd-tl-item--order .bd-tl-dot { background: var(--semantic-500); }
.bd-tl-item--dispatch .bd-tl-dot { background: var(--kinetic-500); }
.bd-tl-item--call .bd-tl-dot { background: var(--dynamic-500); }
.bd-tl-item--callback .bd-tl-dot { background: #9775fa; }
.bd-tl-item--competitor .bd-tl-dot { background: var(--status-error); }
.bd-tl-item--churn .bd-tl-dot { background: #c92a2a; width: 14px; height: 14px; left: -25px; top: 3px; }
.bd-tl-line { position: absolute; left: -19px; top: 18px; bottom: -6px; width: 2px; background: var(--neutral-200); }
.bd-tl-content { padding-left: 12px; }
.bd-tl-time { font-size: 11px; color: var(--neutral-400); font-family: 'SF Mono', monospace; }
.bd-tl-title { font-size: 14px; font-weight: 600; color: var(--neutral-800); margin-top: 2px; }
.bd-tl-desc { font-size: 13px; color: var(--neutral-600); margin-top: 4px; line-height: 1.5; }
.bd-tl-tags { display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap; }
.bd-tl-tag { font-size: 11px; padding: 1px 6px; border-radius: var(--radius-sm); background: var(--neutral-100); color: var(--neutral-600); }

/* Pipeline / Chain */
.bd-chain-wrap { overflow-x: auto; }
.bd-pipeline { display: flex; align-items: flex-start; gap: 0; min-width: 900px; }
.bd-pipe-arrow { font-size: 24px; color: var(--neutral-300); padding: 30px 8px 0; flex-shrink: 0; }
.bd-pipe-step { flex: 1; background: var(--neutral-0); border: 2px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 16px; min-width: 200px; transition: var(--transition-fast); }
.bd-pipe-step--done { border-color: var(--dynamic-300); background: var(--dynamic-50); }
.bd-pipe-step__icon { width: 28px; height: 28px; border-radius: 50%; background: var(--neutral-200); color: var(--neutral-600); display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; margin-bottom: 8px; }
.bd-pipe-step--done .bd-pipe-step__icon { background: var(--dynamic-500); color: #fff; }
.bd-pipe-step__title { font-size: 15px; font-weight: 700; color: var(--neutral-800); }
.bd-pipe-step__sub { font-size: 12px; color: var(--neutral-500); margin-top: 2px; margin-bottom: 10px; }
.bd-pipe-step__detail { display: flex; flex-direction: column; gap: 4px; }
.bd-pipe-kv { display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; }
.bd-pipe-kv__k { color: var(--neutral-500); }
.bd-pipe-kv__v { color: var(--neutral-700); font-weight: 500; }
.bd-pipe-hit { color: var(--dynamic-600); font-weight: 700; }
.bd-pipe-status { padding: 1px 6px; border-radius: var(--radius-sm); font-size: 11px; }
.bd-pipe-status--completed { background: var(--status-success-bg); color: var(--status-success); }
.bd-pipe-status--pending { background: var(--neutral-100); color: var(--neutral-500); }

/* PLACEHOLDER_STYLE4 */

/* Evidence & Rules table */
.bd-table-wrap { overflow-x: auto; }
.bd-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.bd-table th { padding: 8px 12px; text-align: left; font-weight: 600; color: var(--neutral-600); background: var(--neutral-50); border-bottom: 1px solid var(--neutral-200); white-space: nowrap; }
.bd-table td { padding: 8px 12px; border-bottom: 1px solid var(--neutral-50); color: var(--neutral-700); }
.bd-table__row--hit { background: var(--dynamic-50); }
.bd-ev-type { font-size: 11px; padding: 1px 6px; border-radius: var(--radius-sm); font-weight: 500; }
.bd-ev-type--nlp { background: #e7f5ff; color: #1971c2; }
.bd-ev-type--rule { background: #fff3bf; color: #e67700; }
.bd-ev-type--manual { background: #e6fcf5; color: #087f5b; }
.bd-hit-yes { color: var(--status-success); font-weight: 600; }
.bd-hit-no { color: var(--neutral-400); }
.bd-lh-result { font-size: 11px; padding: 1px 6px; border-radius: var(--radius-sm); font-weight: 500; }
.bd-lh-result--hit { background: var(--status-success-bg); color: var(--status-success); }
.bd-lh-result--miss { background: var(--status-error-bg); color: var(--status-error); }
.bd-lh-result--partial { background: var(--status-warning-bg); color: #e67700; }

/* Actions */
.bd-actions-wrap { display: flex; flex-direction: column; gap: 10px; }
.bd-act-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 14px 16px; }
.bd-act-card__header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.bd-act-card__code { font-size: 11px; color: var(--neutral-500); }
.bd-act-card__name { font-size: 14px; font-weight: 600; color: var(--neutral-800); }
.bd-act-card__priority { font-size: 11px; padding: 1px 6px; border-radius: var(--radius-sm); font-weight: 500; }
.bd-act-card__priority--high { background: var(--status-error-bg); color: var(--status-error); }
.bd-act-card__priority--medium { background: var(--status-warning-bg); color: #e67700; }
.bd-act-card__priority--low { background: var(--neutral-100); color: var(--neutral-500); }
.bd-act-card__status { font-size: 11px; padding: 1px 8px; border-radius: var(--radius-full); font-weight: 500; }
.bd-act-card__status--pending_approval { background: #fff8e1; color: #e67700; }
.bd-act-card__status--approved { background: var(--status-info-bg); color: var(--status-info); }
.bd-act-card__status--rejected { background: var(--status-error-bg); color: var(--status-error); }
.bd-act-card__status--executing { background: var(--semantic-50); color: var(--semantic-600); }
.bd-act-card__status--completed { background: var(--status-success-bg); color: var(--status-success); }
.bd-act-card__status--failed { background: var(--status-error-bg); color: var(--status-error); }
.bd-act-card__desc { font-size: 13px; color: var(--neutral-600); margin-top: 6px; }
.bd-act-card__meta { display: flex; gap: 16px; font-size: 11px; color: var(--neutral-400); margin-top: 8px; flex-wrap: wrap; }
.bd-act-card__btns { display: flex; gap: 8px; margin-top: 10px; }

/* Trail */
.bd-trail-wrap { display: flex; flex-direction: column; gap: 0; }
.bd-trail-item { display: grid; grid-template-columns: 140px 100px 1fr 80px; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--neutral-50); font-size: 12px; align-items: center; }
.bd-trail-item__time { color: var(--neutral-500); font-family: 'SF Mono', monospace; font-size: 11px; }
.bd-trail-type-tag { font-size: 11px; padding: 1px 6px; border-radius: var(--radius-sm); font-weight: 500; background: var(--neutral-100); color: var(--neutral-600); }
.bd-trail-type-tag--evidence_extracted { background: #e7f5ff; color: #1971c2; }
.bd-trail-type-tag--logic_hit { background: #fff3bf; color: #e67700; }
.bd-trail-type-tag--action_created { background: var(--semantic-50); color: var(--semantic-600); }
.bd-trail-type-tag--action_approved { background: var(--status-success-bg); color: var(--status-success); }
.bd-trail-type-tag--action_rejected { background: var(--status-error-bg); color: var(--status-error); }
.bd-trail-type-tag--action_executed { background: var(--dynamic-50); color: var(--dynamic-600); }
.bd-trail-type-tag--status_changed { background: #f3f0ff; color: #7048e8; }
.bd-trail-item__detail { color: var(--neutral-700); }
.bd-trail-item__op { color: var(--neutral-400); text-align: right; }

/* Modal */
.bd-select { height: 34px; padding: 0 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: 13px; background: var(--neutral-0); width: 100%; margin-bottom: 12px; }
.bd-modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.bd-modal { background: var(--neutral-0); border-radius: var(--radius-xl); padding: 24px; width: 400px; box-shadow: var(--shadow-xl); }
.bd-modal__title { font-size: 16px; font-weight: 600; margin: 0 0 16px; color: var(--neutral-900); }
.bd-modal__btns { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }

.bd-empty { padding: 40px; text-align: center; color: var(--neutral-400); font-size: 13px; }

/* ── 分析过程 ── */
.bd-analysis-wrap { padding: 16px 0; }
.bd-analysis-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.bd-analysis-running { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--semantic-500); }
.bd-analysis-error { padding: 10px 14px; background: var(--status-error-bg); color: var(--status-error); border-radius: var(--radius-md); font-size: 13px; margin-bottom: 12px; }
.bd-analysis-done { padding: 10px 14px; background: var(--status-success-bg); color: var(--status-success); border-radius: var(--radius-md); font-size: 13px; margin-top: 12px; text-align: center; }

.bd-steps { display: flex; flex-direction: column; gap: 0; }
.bd-step { display: flex; gap: 12px; position: relative; padding-bottom: 20px; }
.bd-step__icon { width: 32px; height: 32px; border-radius: var(--radius-full); display: flex; align-items: center; justify-content: center; flex-shrink: 0; background: var(--neutral-100); color: var(--neutral-500); font-size: 13px; font-weight: 600; z-index: 1; }
.bd-step--loading .bd-step__icon { background: var(--semantic-50); color: var(--semantic-500); }
.bd-step--done .bd-step__icon { background: var(--status-success-bg); color: var(--status-success); }
.bd-step--error .bd-step__icon { background: var(--status-error-bg); color: var(--status-error); }
.bd-step__connector { position: absolute; left: 15px; top: 32px; bottom: 0; width: 2px; background: var(--neutral-200); }
.bd-step--done .bd-step__connector { background: var(--status-success); opacity: 0.3; }
.bd-step__body { flex: 1; min-width: 0; }
.bd-step__title { font-size: 14px; font-weight: 600; color: var(--neutral-800); line-height: 32px; }
.bd-step--pending .bd-step__title { color: var(--neutral-400); }
.bd-step__msg { font-size: 12px; color: var(--neutral-500); margin-top: 4px; }
.bd-step__detail { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.bd-step-tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 11px; background: var(--neutral-100); color: var(--neutral-600); }
.bd-step-tag--hit { background: var(--semantic-50); color: var(--semantic-600); font-weight: 600; }
.bd-step-num { font-size: 12px; }
.bd-step__attribution { margin-top: 8px; }
.bd-step__attr-text { font-family: inherit; font-size: 13px; color: var(--neutral-800); white-space: pre-wrap; margin: 0; padding: 12px; background: var(--semantic-50); border: 1px solid var(--semantic-200); border-radius: var(--radius-md); }
.bd-cursor { animation: bd-blink 0.8s infinite; color: var(--semantic-500); }
@keyframes bd-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

.bd-spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid var(--neutral-200); border-top-color: var(--semantic-500); border-radius: 50%; animation: bd-spin 0.6s linear infinite; }
.bd-spinner--sm { width: 14px; height: 14px; }
@keyframes bd-spin { to { transform: rotate(360deg); } }

/* ── 本体图谱 ── */
.bd-graph-wrap { padding: 16px 0; }
.bd-graph-loading { display: flex; align-items: center; gap: 8px; justify-content: center; padding: 40px; color: var(--neutral-500); font-size: 13px; }
.bd-graph-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
.bd-graph-legend__item { display: flex; align-items: center; gap: 4px; font-size: 11px; color: var(--neutral-600); }
.bd-graph-legend__dot { width: 10px; height: 10px; border-radius: 50%; }
.bd-graph-svg-wrap { border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); background: var(--neutral-0); overflow: auto; }
.bd-graph-svg { display: block; width: 100%; min-width: 500px; }
.bd-graph-info { font-size: 11px; color: var(--neutral-400); margin-top: 8px; }

/* 语音质检 */
.bd-voice-wrap { padding: 4px 0; }
.bd-voice-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.bd-voice-hint { font-size: 13px; color: var(--neutral-500); }
.bd-voice-extra { margin-bottom: 16px; }
.bd-voice-extra__label { font-size: 12px; color: var(--neutral-500); margin-bottom: 6px; }
.bd-voice-textarea { width: 100%; min-height: 80px; padding: 8px 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: 13px; color: var(--neutral-800); background: var(--neutral-0); resize: vertical; box-sizing: border-box; }
.bd-voice-calls { display: flex; flex-direction: column; gap: 12px; }
.bd-voice-call { border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 14px 16px; background: var(--neutral-0); }
.bd-voice-call__meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.bd-voice-call__type { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: var(--radius-full); }
.bd-voice-call__type--engineer { background: #dbeafe; color: #1d4ed8; }
.bd-voice-call__type--callback { background: #d1fae5; color: #065f46; }
.bd-voice-call__time { font-size: 12px; color: var(--neutral-400); }
.bd-voice-call__eng { font-size: 12px; color: var(--neutral-600); }
.bd-voice-call__asr { font-size: 13px; color: var(--neutral-700); line-height: 1.6; background: var(--neutral-50); border-radius: var(--radius-md); padding: 8px 10px; white-space: pre-wrap; max-height: 120px; overflow-y: auto; }
.bd-voice-badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: var(--radius-full); margin-left: auto; }
.bd-voice-badge--pass { background: #d1fae5; color: #065f46; }
.bd-voice-badge--fail { background: #fee2e2; color: #991b1b; }
.bd-voice-badge--warning { background: #fef3c7; color: #92400e; }
.bd-voice-badge--error { background: var(--neutral-100); color: var(--neutral-500); }
.bd-voice-result { margin-top: 12px; border-top: 1px solid var(--neutral-100); padding-top: 12px; }
.bd-voice-result__summary { font-size: 13px; color: var(--neutral-700); margin-bottom: 10px; font-weight: 500; }
.bd-voice-dims { display: flex; flex-direction: column; gap: 6px; }
.bd-voice-dim { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; }
.bd-voice-dim__icon { width: 16px; height: 16px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; margin-top: 1px; }
.bd-voice-dim--pass .bd-voice-dim__icon { color: #10b981; }
.bd-voice-dim--fail .bd-voice-dim__icon { color: #ef4444; }
.bd-voice-dim--na .bd-voice-dim__icon { color: var(--neutral-400); }
.bd-voice-dim__name { font-weight: 600; color: var(--neutral-700); min-width: 64px; flex-shrink: 0; }
.bd-voice-dim__comment { color: var(--neutral-500); }
.bd-voice-risks { margin-top: 10px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.bd-voice-risk-label { font-size: 12px; color: var(--neutral-500); }
.bd-voice-risk-tag { font-size: 11px; background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: var(--radius-full); }
.bd-voice-error { margin-top: 8px; font-size: 12px; color: #ef4444; }
</style>

