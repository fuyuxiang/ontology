import type {
  ScenarioCard,
  SampleDataSource,
  PublishGate,
  ConsumerTarget,
  MonitoringBaseline,
  UploadRecord,
  DataAsset,
  OntologyObjectDraft,
} from '../types/builder'

// ── 三大预置场景 ──
export const SCENARIO_PRESETS: ScenarioCard[] = [
  {
    id: 'refund-root-cause',
    short: '归因',
    title: '退单根因分析',
    description: '基于退单行为本体，自动归因退单原因，输出可执行的服务改善与挽留策略',
    meta: '退单 · 归因 · 挽留',
    tone: 'slate',
  },
  {
    id: 'enterprise-qa',
    short: '问数',
    title: '政企智能问数',
    description: '面向政企客户的自然语言问数场景，通过本体语义层驱动 Text-to-SQL 精准查询',
    meta: '政企 · NL2SQL · 问答',
    tone: 'purple',
  },
  {
    id: 'fttr-renewal',
    short: '续约',
    title: 'FTTR续约策略策划',
    description: '合约到期用户续约保有，按ARPU分档推送个性化续约方案，降低用户流失率',
    meta: '宽带 · 续约 · 营销',
    tone: 'blue',
  },
]

// ── 输入栏占位文案（按场景） ──
export const SCENARIO_PLACEHOLDERS: Record<string, string> = {
  'refund-root-cause': '描述退单场景，或上传退单流程图、业务文档、规则表、POC资料...',
  'enterprise-qa': '描述政企问数场景，或上传政企场景文件、数据模型清单...',
  'fttr-renewal': '描述你的业务场景，例如：提取FTTR合约近1个月内到期用户，按ARPU值分档...',
}

// ── 欢迎语 ──
export const SCENARIO_WELCOME: Record<string, string> = {
  'refund-root-cause':
    '你好！我是本体构建助手，请描述你的业务场景需求，我来帮你拆解用户故事、匹配数据资产并构建本体。\n\n例如：「围绕宽带装机退单构建根因分析本体，结合流程图、业务文档、规则表和外呼数据识别退单原因」',
  'enterprise-qa':
    '你好！我是本体构建助手，请描述你的业务场景需求，我来帮你拆解用户故事、匹配数据资产并构建本体。\n\n例如：「围绕政企 KPI 智能问数及根因分析构建本体，结合要客明细、指标血缘、预算毛利和应收数据定位收入波动原因」',
  'fttr-renewal':
    '你好！我是本体构建助手，请描述你的业务场景需求，我来帮你拆解用户故事、匹配数据资产并构建本体。\n\n例如：「提取FTTR合约近1个月内到期用户，按ARPU值分档，匹配产品进行营销触达」',
}

// ── 资产扫描 6 步 ──
export const SCAN_STEPS = [
  { key: 'intent', label: '识别用户需求', description: '解析场景关键词与业务意图...' },
  { key: 'sensitive', label: '敏感词检测', description: '安全过滤与合规校验...' },
  { key: 'deep_parse', label: '需求深度解析', description: '语义理解与实体抽取...' },
  { key: 'radar_scan', label: '结构化资产扫描', description: '扫描数据中台：数据模型、标签、指标...' },
  { key: 'doc_scan', label: '非结构化文档检索', description: '检索 SOP、FAQ、知识图谱、外呼录音...' },
  { key: 'compose', label: '规范回答', description: '组装资产清单与匹配说明...' },
]

// ── 网络构建动画阶段 ──
export const GRAPH_BUILDING_STEPS = [
  '🔍 识别业务主体...',
  '🏷️ 关联本体属性...',
  '🔗 建立关系连线...',
  '⚙️ 生成触发条件...',
  '⚡ 编排执行动作...',
]

// ── 水合演练 4 阶段 ──
export const HYDRATION_PHASES = [
  { key: 'ingest' as const, label: '数据接入', color: '#6366f1' },
  { key: 'instantiate' as const, label: '本体实例化', color: '#2E5BFF' },
  { key: 'match' as const, label: '关系映射验证', color: '#f59e0b' },
  { key: 'strategy' as const, label: '策略输出', color: '#10b981' },
]

// ── 退单场景样例数据源 ──
export const SAMPLE_DATA_SOURCES: SampleDataSource[] = [
  { id: 'ds-install-order', fileName: '20260404-样例数据.xlsx / 装移机装维工单数据(日)', rows: 10, columns: 55, system: 'CBSS', targetClass: 'InstallOrder' },
  { id: 'ds-dispatch', fileName: '20260404-样例数据.xlsx / 修障装维工单数据(日)', rows: 10, columns: 42, system: 'CBSS', targetClass: 'DispatchRecord' },
  { id: 'ds-callback', fileName: '20260404-样例数据.xlsx / 语音转文本采集表(日)', rows: 12, columns: 19, system: '中台', targetClass: 'CallbackCall' },
  { id: 'ds-pending-addr', fileName: '20260404-样例数据.xlsx / 待装订单信息表(日)', rows: 10, columns: 39, system: 'CBSS', targetClass: 'PendingAddress' },
  { id: 'ds-resource-order', fileName: '20260404-样例数据.xlsx / 固网装机资源订单表(日)', rows: 15, columns: 35, system: 'CBSS', targetClass: 'Address' },
  { id: 'ds-appoint-order', fileName: '20260404-样例数据.xlsx / 固网装机预约订单表(日)', rows: 20, columns: 20, system: 'CBSS', targetClass: 'DispatchRecord' },
  { id: 'ds-complaint', fileName: '20260404-样例数据.xlsx / 投诉工单场景(日)', rows: 20, columns: 96, system: 'CBSS', targetClass: 'InstallChurn' },
  { id: 'ds-vip-list', fileName: '20260404-样例数据.xlsx / CBSS高星级长高用户清单(月)', rows: 40, columns: 19, system: 'CBSS', targetClass: 'Customer' },
  { id: 'ds-install-detail', fileName: '20260404-样例数据.xlsx / 装移机装维宽表明细(日)', rows: 30, columns: 70, system: 'CBSS', targetClass: 'InstallOrder' },
  { id: 'ds-bss-main', fileName: '20260404-样例数据.xlsx / Bss业务台账主表(日)', rows: 30, columns: 85, system: 'BSS' },
  { id: 'ds-cbss-history', fileName: '20260404-样例数据.xlsx / CBSS业务台账主表历史(日)', rows: 30, columns: 85, system: 'CBSS' },
  { id: 'ds-product', fileName: '20260404-样例数据.xlsx / CBSS产品发布表(月)', rows: 30, columns: 18, system: 'CBSS', targetClass: 'Product' },
  { id: 'ds-arrear', fileName: '20260404-样例数据.xlsx / cBss用户欠费信息表(日)', rows: 25, columns: 22, system: 'CBSS' },
  { id: 'ds-agent', fileName: '20260404-样例数据.xlsx / 人工坐席接触记录信息(日)', rows: 22, columns: 28, system: '中台' },
  { id: 'ds-channel', fileName: '20260404-样例数据.xlsx / 渠道合作方信息表(日)', rows: 18, columns: 16, system: 'CBSS' },
  { id: 'ds-callback-tx', fileName: '20260404-样例数据.xlsx / 回访外呼转写明细(日)', rows: 24, columns: 18, system: '中台' },
  { id: 'ds-audit-result', fileName: '20260404-样例数据.xlsx / 退单稽核结果明细(日)', rows: 18, columns: 24, system: '稽核中心' },
  { id: 'ds-retain-result', fileName: '20260404-样例数据.xlsx / 退单挽留执行结果(日)', rows: 18, columns: 22, system: '运营平台' },
  { id: 'ds-iron-army', fileName: '20260404-样例数据.xlsx / [网格]八大铁军有效人员明细数据(日)', rows: 16, columns: 25, system: 'OA' },
  { id: 'ds-appoint-change', fileName: '20260404-样例数据.xlsx / 预约变更记录(日)', rows: 16, columns: 18, system: 'CBSS' },
  { id: 'ds-addr-audit', fileName: '20260404-样例数据.xlsx / 地址资源核查结果(日)', rows: 18, columns: 20, system: 'CBSS' },
]

// ── 发布门禁（默认值） ──
export const DEFAULT_PUBLISH_GATES: PublishGate[] = [
  { key: 'structure', label: '本体结构完整', desc: '本体 0 个', pass: false },
  { key: 'walkthrough', label: '走测全部通过', desc: '通过节点 0 / 0', pass: false },
  { key: 'drill', label: '演练验证', desc: '实体 0 · 关系 0', pass: false },
  { key: 'hydration_report', label: '水合验证报告已归档', desc: '快照 v0.1', pass: false },
  { key: 'expert_sign', label: '双专家签字记录可追溯', desc: '审批人 + 走测人', pass: false },
  { key: 'version_consistency', label: '版本号一致', desc: '本体结构 / 本体引擎 / 集市统一为 v0.1', pass: false },
  { key: 'rollback_ready', label: '回滚方案已准备', desc: '回滚目标：v0.0', pass: false },
]

// ── 消费方对接 ──
export const CONSUMER_TARGETS: ConsumerTarget[] = [
  { name: 'AIP 场景平台', usage: '消费本体对象，编排工作流执行', status: '⬜ 待对接' },
  { name: 'AI 助手', usage: '本体查询 + 推理解释（SPARQL接口）', status: '⬜ 待对接' },
  { name: 'Agent Harness', usage: 'A/B 测试 + 反馈闭环', status: '⬜ 待对接' },
  { name: '其他省分', usage: '从本体集市订购，多租户隔离', status: '⬜ 待开放' },
]

// ── 监控基线（按场景） ──
export const MONITORING_BASELINES: Record<string, MonitoringBaseline[]> = {
  'refund-root-cause': [
    { label: '归因准确率', value: '94.6%', target: '目标 90% · 日级监控', level: 'success' },
    { label: '高置信归因占比', value: '78.2%', target: '目标 75% · 日级监控', level: 'success' },
    { label: '回访覆盖率', value: '85.4%', target: '目标 80% · 实时监控', level: 'info' },
    { label: '根因解释覆盖率', value: '88.1%', target: '阈值 < 85% 告警', level: 'warning' },
  ],
  'enterprise-qa': [
    { label: '问数命中率', value: '92.3%', target: '目标 90% · 日级监控', level: 'success' },
    { label: '字段映射准确率', value: '98.6%', target: '目标 95% · 日级监控', level: 'success' },
    { label: '推理成功率', value: '95.4%', target: '阈值 < 90% 告警', level: 'warning' },
    { label: '查询 P99 延迟', value: '480ms', target: '阈值 > 1s 告警', level: 'info' },
  ],
  'fttr-renewal': [
    { label: '续约转化率', value: '12.6%', target: '目标 10% · 日级监控', level: 'success' },
    { label: '触达成功率', value: '82.4%', target: '目标 80% · 日级监控', level: 'success' },
    { label: 'ARPU 提升幅度', value: '+18.2%', target: '基线 + 15%', level: 'info' },
    { label: '续约成功数', value: '2,840 户', target: '日级监控', level: 'info' },
  ],
}

// ── 演示上传记录（builder-upload-records） ──
export const DEMO_UPLOAD_RECORDS: UploadRecord[] = [
  {
    id: 'demo-upload-1', fileName: 'FTTR续约SOP_v3.pdf', fileType: 'PDF', fileSize: '2.3 MB',
    sourceOntology: 'FTTR续约策略策划 v2.0', scenarioName: 'FTTR续约策划',
    uploadedAt: '2026-04-20T09:12:00.000Z',
    status: 'completed', statusText: '已提取规则（24条）',
    extractedSummary: '续约策略、触达约束与产品匹配规则已提取',
    extractedRules: 24, extractedFields: 0, mimeCategory: 'unstructured',
  },
  {
    id: 'demo-upload-2', fileName: '用户ARPU分层标准.xlsx', fileType: 'XLSX', fileSize: '156 KB',
    sourceOntology: 'FTTR续约策略策划 v2.0', scenarioName: 'FTTR续约策划',
    uploadedAt: '2026-04-20T09:18:00.000Z',
    status: 'completed', statusText: '已提取结构（8字段）',
    extractedSummary: 'ARPU分层口径、字段结构与示例值已提取',
    extractedRules: 0, extractedFields: 8, mimeCategory: 'structured',
  },
  {
    id: 'demo-upload-3', fileName: '政企问数实体关系图.png', fileType: 'PNG', fileSize: '1.8 MB',
    sourceOntology: '政企智能问数本体', scenarioName: '政企智能问数',
    uploadedAt: '2026-04-20T09:26:00.000Z',
    status: 'parsing', statusText: 'AI 解析中...',
    extractedSummary: '图片关系抽取正在进行',
    extractedRules: 0, extractedFields: 0, mimeCategory: 'image',
  },
  {
    id: 'demo-upload-4', fileName: '退单归因分析SOP.pdf', fileType: 'PDF', fileSize: '3.1 MB',
    sourceOntology: '退单根因分析本体', scenarioName: '退单根因分析',
    uploadedAt: '2026-04-20T09:42:00.000Z',
    status: 'completed', statusText: '已提取规则（18条）',
    extractedSummary: '退单原因分层、派单路径与闭环规则已提取',
    extractedRules: 18, extractedFields: 0, mimeCategory: 'unstructured',
  },
  {
    id: 'demo-upload-5', fileName: '退单分类对照表.xlsx', fileType: 'XLSX', fileSize: '89 KB',
    sourceOntology: '退单根因分析本体', scenarioName: '退单根因分析',
    uploadedAt: '2026-04-20T09:48:00.000Z',
    status: 'failed', statusText: '解析失败',
    extractedSummary: '文件存在合并单元格，需重新解析或上传规范模板',
    extractedRules: 0, extractedFields: 0, mimeCategory: 'structured',
  },
]

// ── 资产清单（mock，按场景） ──
export const SCENARIO_ASSETS: Record<string, DataAsset[]> = {
  'refund-root-cause': [
    {
      id: 'asset-refund-flow', name: '宽带装机退单流程图', type: '业务文档',
      domain: '退单场景资料', subscribed: false, category: 'unstructured',
      fileType: 'png', fileSize: '流程图', ontologyTarget: 'R-box',
      description: '装机受理 → 资源核查 → 派单 → 走测 → 退单分支与回访闭环',
      distilledRules: ['资源不足触发退单', '4小时未派单转人工坐席', '装机失败需回访闭环'],
    },
    {
      id: 'asset-refund-doc', name: '退单原因分类业务文档', type: '业务文档',
      domain: '退单场景资料', subscribed: false, category: 'unstructured',
      fileType: 'pdf', fileSize: '业务文档', ontologyTarget: 'R-box',
      description: '退单原因分类（资源/产品/服务）、判定口径与样例',
      distilledRules: ['资源类退单：地址不可达、楼栋未覆盖', '产品类退单：套餐不符合预期', '服务类退单：装维超期/质量不达标'],
    },
    {
      id: 'asset-refund-rule', name: '装机走测规则表', type: '规则表',
      domain: '退单场景资料', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: '规则表', ontologyTarget: 'R-box',
      description: '走测拍照、信号强度、网速 6 大检查项与判定阈值',
      fields: [
        { name: '检查项', en: 'check_item', type: '枚举' },
        { name: '阈值', en: 'threshold', type: '数值' },
        { name: '判定结果', en: 'verdict', type: '枚举' },
      ],
    },
    {
      id: 'asset-callback-call', name: '中台回访-外呼录音订单外呼数据', type: '数据模型',
      domain: '场景外呼数据', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: '外呼明细', ontologyTarget: 'A-box',
      description: '装维外呼、回访外呼、营销外呼三类合并明细，支持退单原因复核',
      fields: [
        { name: '业务工单号', en: 'order_no', type: '字符串' },
        { name: '外呼类型', en: 'call_type', type: '枚举' },
        { name: '通话时长', en: 'duration', type: '数值' },
        { name: '中台单号', en: 'mid_no', type: '字符串' },
      ],
    },
    {
      id: 'asset-customer', name: '客户主信息（CBSS）', type: '数据模型',
      domain: 'CBSS 业务主数据', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: '客户主表', ontologyTarget: 'T-box',
      description: '客户身份、星级、ARPU 与归属地，支撑客户对象 Tier1',
      fields: [
        { name: '客户ID', en: 'customer_id', type: '主键' },
        { name: '姓名', en: 'name', type: '字符串' },
        { name: '星级', en: 'star_level', type: '枚举' },
        { name: 'ARPU', en: 'arpu', type: '数值' },
      ],
    },
    {
      id: 'asset-product', name: '产品目录与资费', type: '数据模型',
      domain: '产品目录库', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: '产品资费', ontologyTarget: 'T-box',
      description: '宽带 / FTTR / 融合产品族、档位、资费',
      fields: [
        { name: '产品ID', en: 'product_id', type: '主键' },
        { name: '产品族', en: 'product_family', type: '枚举' },
        { name: '档位', en: 'tier', type: '枚举' },
        { name: '月费', en: 'monthly_fee', type: '数值' },
      ],
    },
  ],
  'enterprise-qa': [
    {
      id: 'asset-vip-detail', name: '政企要客明细清单', type: '数据模型',
      domain: '政企客户库', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: '要客明细', ontologyTarget: 'T-box',
      description: '政企客户群体的核心字段，含客户经理、行业、归属省分',
    },
    {
      id: 'asset-kpi-lineage', name: '指标血缘字典', type: '指标',
      domain: '指标体系', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: '指标血缘', ontologyTarget: 'T-box',
      description: '收入 / 毛利 / 应收口径、计算公式、上下游来源',
    },
    {
      id: 'asset-budget', name: '预算达成与缺口', type: '指标',
      domain: '预算体系', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: '预算达成', ontologyTarget: 'A-box',
      description: '月度 / 季度预算、达成率、同比环比',
    },
    {
      id: 'asset-qa-doc', name: '政企问数 SOP', type: '业务文档',
      domain: '问数知识库', subscribed: false, category: 'unstructured',
      fileType: 'pdf', fileSize: '问数 SOP', ontologyTarget: 'R-box',
      description: '问数标准话术、字段映射与口径说明',
    },
  ],
  'fttr-renewal': [
    {
      id: 'asset-fttr-renew-doc', name: 'FTTR续约策略策划文档', type: '业务文档',
      domain: 'FTTR续约资料', subscribed: false, category: 'unstructured',
      fileType: 'pdf', fileSize: '续约策略', ontologyTarget: 'R-box',
      description: 'FTTR 到期续约 4 月闭环策略、产品白名单与触达约束',
    },
    {
      id: 'asset-arpu-tier', name: '用户ARPU分层标准.xlsx', type: '规则表',
      domain: 'FTTR续约资料', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: 'ARPU 分层', ontologyTarget: 'R-box',
      description: 'ARPU 分层口径、档位界定、产品匹配建议',
    },
    {
      id: 'asset-product-whitelist', name: '产品白名单（FTTR到期续约4月闭环）', type: '数据模型',
      domain: '产品目录库', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: '产品白名单 4449行', ontologyTarget: 'T-box',
      description: 'FTTR 续约推荐产品白名单，含速率、档位、资费',
    },
    {
      id: 'asset-fttr-customer', name: 'FTTR用户主信息', type: '数据模型',
      domain: '宽带客户库', subscribed: false, category: 'structured',
      fileType: 'xlsx', fileSize: '客户主表', ontologyTarget: 'T-box',
      description: '宽带 / FTTR 在网客户、合约期、ARPU、归属地',
    },
  ],
}

// ── 默认对象类型预设（按场景） ──
export const SCENARIO_CLASS_PRESETS: Record<string, Array<Partial<OntologyObjectDraft>>> = {
  'refund-root-cause': [
    { name: 'Customer', displayName: '客户', tier: 1, primaryKey: 'customer_id', icon: '👤', description: '客户主信息，含星级、ARPU、归属地', instanceCount: 12500 },
    { name: 'Product', displayName: '产品', tier: 1, primaryKey: 'product_id', icon: '📦', description: '宽带 / FTTR / 融合产品族', instanceCount: 320 },
    { name: 'Address', displayName: '地址', tier: 1, primaryKey: 'addr_id', icon: '📍', description: '装机地址主信息', instanceCount: 9800 },
    { name: 'WorkOrder', displayName: '工单', tier: 1, primaryKey: 'order_no', icon: '📝', description: '业务工单台账', instanceCount: 6400 },
    { name: 'PendingAddress', displayName: '待装地址', tier: 2, primaryKey: 'pending_id', icon: '🏠', description: '资源未到位的待装地址记录', instanceCount: 1240 },
    { name: 'InstallChurn', displayName: '宽带装机退单', tier: 3, primaryKey: 'churn_id', icon: '⚠️', description: '退单事件记录', instanceCount: 480 },
    { name: 'CallbackCall', displayName: '回访外呼', tier: 3, primaryKey: 'call_id', icon: '📞', description: '装维 / 回访 / 营销外呼合并明细', instanceCount: 1820 },
    { name: 'Engineer', displayName: '工程师', tier: 2, primaryKey: 'eng_id', icon: '🛠', description: '装维工程师档案', instanceCount: 320 },
    { name: 'DispatchRecord', displayName: '派单记录', tier: 2, primaryKey: 'dispatch_id', icon: '🚚', description: '工单派发与执行记录', instanceCount: 2100 },
  ],
  'enterprise-qa': [
    { name: 'KpiIndicator', displayName: '指标体系', tier: 1, primaryKey: 'kpi_id', icon: '📊', description: '收入 / 毛利 / 应收等指标', instanceCount: 320 },
    { name: 'EnterpriseCustomerSegment', displayName: '政企客户群体', tier: 1, primaryKey: 'seg_id', icon: '🏢', description: '政企客户分群', instanceCount: 56 },
    { name: 'ProductService', displayName: '产品服务', tier: 1, primaryKey: 'service_id', icon: '🛰', description: '联网通信、ICT、物联等', instanceCount: 180 },
    { name: 'Project', displayName: '项目', tier: 2, primaryKey: 'project_id', icon: '📁', description: '政企项目台账', instanceCount: 240 },
    { name: 'Opportunity', displayName: '商机', tier: 2, primaryKey: 'opp_id', icon: '💡', description: '商机/线索台账', instanceCount: 410 },
    { name: 'Contract', displayName: '合同', tier: 2, primaryKey: 'contract_id', icon: '📄', description: '政企合同信息', instanceCount: 280 },
    { name: 'AccountManager', displayName: '客户经理', tier: 2, primaryKey: 'am_id', icon: '🧑‍💼', description: '客户经理档案', instanceCount: 120 },
    { name: 'BizEvent', displayName: '业务事件', tier: 3, primaryKey: 'event_id', icon: '⚡', description: '竞标 / 政策 / 流失等业务事件', instanceCount: 320 },
    { name: 'RegionalOrg', displayName: '地域组织', tier: 1, primaryKey: 'org_id', icon: '🗺', description: '省/市/区县组织维度', instanceCount: 380 },
  ],
  'fttr-renewal': [
    { name: 'Customer', displayName: '客户', tier: 1, primaryKey: 'customer_id', icon: '👤', description: '宽带 / FTTR 在网客户', instanceCount: 8800 },
    { name: 'Contract', displayName: '合约', tier: 1, primaryKey: 'contract_id', icon: '📄', description: '客户在签合约与到期日期', instanceCount: 9200 },
    { name: 'Product', displayName: '产品', tier: 1, primaryKey: 'product_id', icon: '📦', description: 'FTTR 续约推荐产品族', instanceCount: 280 },
    { name: 'CustomerSegment', displayName: '客户分群', tier: 2, primaryKey: 'seg_id', icon: '🎯', description: '按 ARPU 分档的客户分群', instanceCount: 12 },
    { name: 'MarketingScript', displayName: '营销话术', tier: 2, primaryKey: 'script_id', icon: '💬', description: '续约话术模板', instanceCount: 26 },
    { name: 'Touchpoint', displayName: '触点', tier: 2, primaryKey: 'tp_id', icon: '📡', description: '短信 / 外呼 / App 推送', instanceCount: 6 },
    { name: 'TouchpointExecution', displayName: '触点执行记录', tier: 3, primaryKey: 'exec_id', icon: '🧾', description: '续约触达执行明细', instanceCount: 4100 },
    { name: 'CampaignResult', displayName: '策略执行结果', tier: 3, primaryKey: 'result_id', icon: '🏁', description: '续约策略执行结果与转化', instanceCount: 1820 },
  ],
}

// ── 关系预设 ──
export const SCENARIO_RELATION_PRESETS: Record<string, Array<{ source: string; target: string; name: string; displayName: string; cardinality: '1:1'|'1:N'|'N:N' }>> = {
  'refund-root-cause': [
    { source: 'Customer', target: 'WorkOrder', name: 'placedOrder', displayName: '产生工单', cardinality: '1:N' },
    { source: 'WorkOrder', target: 'Address', name: 'targetsAddress', displayName: '关联地址', cardinality: 'N:N' },
    { source: 'WorkOrder', target: 'PendingAddress', name: 'mapsPending', displayName: '关联待装地址', cardinality: '1:N' },
    { source: 'WorkOrder', target: 'DispatchRecord', name: 'dispatchedAs', displayName: '产生派单', cardinality: '1:N' },
    { source: 'DispatchRecord', target: 'Engineer', name: 'assignedTo', displayName: '指派工程师', cardinality: 'N:N' },
    { source: 'WorkOrder', target: 'InstallChurn', name: 'producedChurn', displayName: '产生退单', cardinality: '1:1' },
    { source: 'InstallChurn', target: 'CallbackCall', name: 'triggersCallback', displayName: '产生回访外呼', cardinality: '1:N' },
    { source: 'Customer', target: 'Product', name: 'subscribedTo', displayName: '订购产品', cardinality: '1:N' },
  ],
  'enterprise-qa': [
    { source: 'EnterpriseCustomerSegment', target: 'AccountManager', name: 'managedBy', displayName: '由客户经理负责', cardinality: 'N:N' },
    { source: 'EnterpriseCustomerSegment', target: 'Contract', name: 'holdsContract', displayName: '持有合同', cardinality: '1:N' },
    { source: 'Contract', target: 'ProductService', name: 'coversService', displayName: '覆盖服务', cardinality: '1:N' },
    { source: 'Project', target: 'Opportunity', name: 'derivedFrom', displayName: '来源于商机', cardinality: '1:1' },
    { source: 'BizEvent', target: 'AccountManager', name: 'assignedAm', displayName: '事件-关联客户经理', cardinality: 'N:N' },
    { source: 'BizEvent', target: 'RegionalOrg', name: 'impactsRegion', displayName: '事件-关联地域组织', cardinality: 'N:N' },
    { source: 'KpiIndicator', target: 'EnterpriseCustomerSegment', name: 'measuresSegment', displayName: '度量客户群体', cardinality: 'N:N' },
  ],
  'fttr-renewal': [
    { source: 'Customer', target: 'Contract', name: 'hasContract', displayName: '持有合约', cardinality: '1:N' },
    { source: 'Customer', target: 'CustomerSegment', name: 'inSegment', displayName: '归属分群', cardinality: 'N:N' },
    { source: 'CustomerSegment', target: 'Product', name: 'recommendsProduct', displayName: '推荐产品', cardinality: 'N:N' },
    { source: 'CustomerSegment', target: 'MarketingScript', name: 'usesScript', displayName: '使用话术', cardinality: 'N:N' },
    { source: 'MarketingScript', target: 'Touchpoint', name: 'reachesVia', displayName: '通过触点送达', cardinality: 'N:N' },
    { source: 'Touchpoint', target: 'TouchpointExecution', name: 'executedAs', displayName: '触点执行', cardinality: '1:N' },
    { source: 'TouchpointExecution', target: 'CampaignResult', name: 'producesResult', displayName: '产生执行结果', cardinality: '1:1' },
  ],
}

// ── 默认用户故事（按场景） ──
export const SCENARIO_STORIES: Record<string, Array<{ asRole: string; iWant: string; soThat: string; keywords: string[] }>> = {
  'refund-root-cause': [
    { asRole: '装维主管', iWant: '识别每一笔宽带装机退单的根因', soThat: '为下次装机制定改善动作并降低退单率', keywords: ['退单', '根因', '装机'] },
    { asRole: '资源运营', iWant: '盘点退单的资源类原因占比', soThat: '驱动楼栋光纤覆盖与待装库存优化', keywords: ['资源', '楼栋', '待装'] },
    { asRole: '中台坐席', iWant: '基于外呼录音复核退单原因', soThat: '降低人工逐单判断成本与误差', keywords: ['外呼', '复核', '回访'] },
    { asRole: '运营负责人', iWant: '执行挽留动作并跟踪闭环结果', soThat: '提升退单挽留转化率', keywords: ['挽留', '闭环', '转化'] },
  ],
  'enterprise-qa': [
    { asRole: '政企省经营负责人', iWant: '通过自然语言询问任意指标的同环比', soThat: '快速判断收入波动并定位归因', keywords: ['问数', '同环比', '归因'] },
    { asRole: '政企客户经理', iWant: '查询自己负责客户群体的预算达成', soThat: '推动客户业务增长与缺口跟进', keywords: ['客户经理', '预算', '达成'] },
    { asRole: '财务分析师', iWant: '基于本体语义层做毛利与应收交叉分析', soThat: '识别毛利下滑的具体业务事件', keywords: ['毛利', '应收', '事件'] },
  ],
  'fttr-renewal': [
    { asRole: '宽带运营经理', iWant: '提取FTTR合约近1个月内到期用户', soThat: '提前 30 天启动续约保有动作', keywords: ['FTTR', '到期', '续约'] },
    { asRole: '营销策划', iWant: '按ARPU值分档匹配产品白名单', soThat: '为不同价值用户推送差异化方案', keywords: ['ARPU', '分档', '白名单'] },
    { asRole: '触达运营', iWant: '通过短信 / 外呼 / App 多触点送达', soThat: '提升续约触达成功率与转化', keywords: ['触点', '送达', '转化'] },
  ],
}
