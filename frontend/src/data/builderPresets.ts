import type {
  ScenarioCard,
  PublishGate,
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

// ── 发布门禁（默认值） ──
export const DEFAULT_PUBLISH_GATES: PublishGate[] = [
  { key: 'structure', label: '本体结构完整', desc: '本体 0 个', pass: false },
  { key: 'drill', label: '水合演练通过', desc: '未演练', pass: false },
  { key: 'version_ready', label: '版本就绪', desc: '版本号自动生成', pass: true },
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
