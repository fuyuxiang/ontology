"""数据工坊 — 血缘大图静态种子数据。

与产品演示版（/Users/fuyuxiang/Desktop/html/assets/DataFoundry-*.js）
中的 Cn / Tn / Dn 三个数据结构一一对应：

- ROWS         对应 Cn — 一行串一条 数据源 → ETL → 本体 → 应用 的链路
- CROSS_EDGES  对应 Tn — 本体节点之间的横向虚线引用（业务概念派生关系）
- FIELD_LINEAGE 对应 Dn — 每个本体对象的字段级血缘（多张源表 + 字段映射）

未来如要从仓库元数据 / 实体属性映射动态生成，把这三个 dict 替换成查询结果即可。
"""

from typing import TypedDict


class LineageRow(TypedDict):
    key: str
    source: str
    etl: str
    ontologyId: str
    objectName: str
    ontologyLabel: str
    tier: int
    app: str


class CrossEdge(TypedDict):
    id: str
    source: str
    target: str


class FieldMapping(TypedDict):
    from_: str
    to: str
    apiName: str
    type: str


class FieldLineageGroup(TypedDict):
    source: str
    fields: list[FieldMapping]


ROWS: list[LineageRow] = [
    {"key": "customer", "source": "B域数仓\n客户主表", "etl": "客户主数据清洗",
     "ontologyId": "lo-cust", "objectName": "Customer", "ontologyLabel": "客户", "tier": 1, "app": "客户洞察"},
    {"key": "contract", "source": "全客加工\n到期明细", "etl": "到期合约加工",
     "ontologyId": "lo-contract", "objectName": "Contract", "ontologyLabel": "合约", "tier": 1, "app": "到期推理"},
    {"key": "segment", "source": "标签库\n标签集市", "etl": "客群标签加工",
     "ontologyId": "lo-seg", "objectName": "Segment", "ontologyLabel": "客群分类", "tier": 2, "app": "客群洞察"},
    {"key": "strategy", "source": "全客加工\n策略池", "etl": "策略池加工",
     "ontologyId": "lo-strat", "objectName": "Strategy", "ontologyLabel": "续约策略", "tier": 1, "app": "策略编排"},
    {"key": "moment", "source": "全客加工\n波次计划", "etl": "波次时机加工",
     "ontologyId": "lo-moment", "objectName": "MarketingMoment", "ontologyLabel": "营销时机", "tier": 3, "app": "波次编排"},
    {"key": "script", "source": "全客加工\n话术模板", "etl": "话术模板解析",
     "ontologyId": "lo-script", "objectName": "Script", "ontologyLabel": "话术模板", "tier": 3, "app": "话术生成"},
    {"key": "touch", "source": "全客/公众中台\n触达日志", "etl": "触达日志解析",
     "ontologyId": "lo-touch", "objectName": "TouchEvent", "ontologyLabel": "触达事件", "tier": 3, "app": "触达执行"},
    {"key": "order", "source": "B域数仓\n订单结果", "etl": "交易订单归一",
     "ontologyId": "lo-order", "objectName": "Order", "ontologyLabel": "订单", "tier": 1, "app": "转化评估"},
    {"key": "workorder", "source": "公众中台\n工单记录", "etl": "工单状态回写",
     "ontologyId": "lo-workorder", "objectName": "WorkOrder", "ontologyLabel": "工单", "tier": 1, "app": "工单执行"},
    {"key": "household", "source": "数字沙盘/O域\n空间质量", "etl": "空间质量提取",
     "ontologyId": "lo-household", "objectName": "HouseholdGroup", "ontologyLabel": "家庭群组", "tier": 3, "app": "网络画像"},
    {"key": "kpi", "source": "指标集市\n经分应用", "etl": "指标口径汇总",
     "ontologyId": "lo-kpi", "objectName": "KPIIndicatorValue", "ontologyLabel": "指标度量值", "tier": 3, "app": "经营看板"},
]


CROSS_EDGES: list[CrossEdge] = [
    {"id": "lr-cust-contract", "source": "lo-cust", "target": "lo-contract"},
    {"id": "lr-cust-seg", "source": "lo-cust", "target": "lo-seg"},
    {"id": "lr-seg-strategy", "source": "lo-seg", "target": "lo-strat"},
    {"id": "lr-contract-moment", "source": "lo-contract", "target": "lo-moment"},
    {"id": "lr-strategy-script", "source": "lo-strat", "target": "lo-script"},
    {"id": "lr-script-touch", "source": "lo-script", "target": "lo-touch"},
    {"id": "lr-touch-order", "source": "lo-touch", "target": "lo-order"},
    {"id": "lr-workorder-touch", "source": "lo-workorder", "target": "lo-touch"},
]


# 字段级血缘 — key 是 ontologyId
FIELD_LINEAGE: dict[str, list[FieldLineageGroup]] = {
    "lo-cust": [{
        "source": "数据中台-B域数仓 → DWA_V_D_CUS_CB_USER_INFO",
        "fields": [
            {"from_": "USER_ID", "to": "用户ID", "apiName": "user_id", "type": "STRING"},
            {"from_": "CUST_NAME", "to": "客户姓名", "apiName": "customer_name", "type": "STRING"},
            {"from_": "MOBILE_NO", "to": "联系电话", "apiName": "contact_phone", "type": "STRING"},
            {"from_": "CUST_LEVEL", "to": "客户星级", "apiName": "customer_level", "type": "STRING"},
            {"from_": "REGION_CODE", "to": "归属区域", "apiName": "region_ref", "type": "FK"},
        ],
    }],
    "lo-order": [
        {"source": "数据中台-B域数仓 → DWD_D_EVT_CB_TRADE", "fields": [
            {"from_": "TRADE_ID", "to": "订单ID", "apiName": "order_id", "type": "STRING"},
            {"from_": "USER_ID", "to": "关联客户", "apiName": "customer_ref", "type": "FK"},
            {"from_": "PRODUCT_CODE", "to": "下单产品", "apiName": "product_ref", "type": "FK"},
            {"from_": "ORDER_RESULT", "to": "订单结果码", "apiName": "order_result", "type": "ENUM"},
            {"from_": "ORDER_DT", "to": "下单时间", "apiName": "order_time", "type": "TIMESTAMP"},
            {"from_": "TOTAL_AMT", "to": "订单金额(元)", "apiName": "amount", "type": "DECIMAL"},
        ]},
        {"source": "数据中台-全客数据加工 → ADS_QK_FTTR_ORDER_RESULT_PT", "fields": [
            {"from_": "ORDER_ID", "to": "订单ID", "apiName": "order_id", "type": "STRING"},
            {"from_": "USER_ID", "to": "关联客户", "apiName": "customer_ref", "type": "FK"},
            {"from_": "ORDER_RESULT", "to": "订单结果码", "apiName": "order_result", "type": "ENUM"},
            {"from_": "PRODUCT_CODE", "to": "下单产品", "apiName": "product_ref", "type": "FK"},
        ]},
    ],
    "lo-contract": [{
        "source": "数据中台-全客数据加工 → ADS_QK_FTTR_EXPIRE_USER_PT",
        "fields": [
            {"from_": "CONTRACT_ID", "to": "合约ID", "apiName": "contract_id", "type": "STRING"},
            {"from_": "USER_ID", "to": "客户引用", "apiName": "customer_ref", "type": "FK"},
            {"from_": "CONTRACT_START_DT", "to": "合约开始日", "apiName": "start_date", "type": "DATE"},
            {"from_": "JT00285", "to": "合约到期日", "apiName": "end_date", "type": "DATE"},
            {"from_": "DAYS_TO_EXPIRE", "to": "距到期天数", "apiName": "days_to_expire", "type": "INT"},
            {"from_": "CONTRACT_TYPE", "to": "合约类型", "apiName": "contract_type", "type": "STRING"},
        ],
    }],
    "lo-seg": [{
        "source": "数据中台-标签库 → TAG_CHURN_RISK_D",
        "fields": [
            {"from_": "SEGMENT_CODE", "to": "客群码", "apiName": "segment_code", "type": "STRING"},
            {"from_": "SEGMENT_NAME", "to": "客群中文名", "apiName": "segment_name", "type": "STRING"},
            {"from_": "CREATE_MODE", "to": "生成方式", "apiName": "create_mode", "type": "STRING"},
            {"from_": "CUSTOMER_COUNT", "to": "覆盖客户数", "apiName": "includes_customer_count", "type": "INT"},
            {"from_": "ORDER_CVR", "to": "订单口径转化率", "apiName": "conversion_rate_order", "type": "DECIMAL"},
        ],
    }],
    "lo-strat": [{
        "source": "数据中台-全客数据加工 → ADS_QK_FTTR_STRATEGY_PT",
        "fields": [
            {"from_": "PAR_STRATEGY_ID", "to": "母策略ID", "apiName": "par_strategy_id", "type": "STRING"},
            {"from_": "STRATEGY_NAME", "to": "策略名称", "apiName": "strategy_name", "type": "STRING"},
            {"from_": "SCOPE", "to": "策略范围", "apiName": "scope", "type": "STRING"},
            {"from_": "TARGET_SEGMENT", "to": "目标客群", "apiName": "target_segment_ref", "type": "FK"},
            {"from_": "SQL_CONDITIONS", "to": "SQL入池条件", "apiName": "sql_conditions", "type": "TEXT"},
            {"from_": "DEFAULT_CHANNEL", "to": "默认触点渠道", "apiName": "default_channel_ref", "type": "FK"},
        ],
    }],
    "lo-moment": [{
        "source": "数据中台-全客数据加工 → ADS_QK_WAVE_PLAN",
        "fields": [
            {"from_": "MOMENT_ID", "to": "时机ID", "apiName": "moment_id", "type": "STRING"},
            {"from_": "USER_ID", "to": "客户引用", "apiName": "customer_ref", "type": "FK"},
            {"from_": "CONTRACT_ID", "to": "合约引用", "apiName": "contract_ref", "type": "FK"},
            {"from_": "TRIGGER_TYPE", "to": "触发类型", "apiName": "trigger_type", "type": "STRING"},
            {"from_": "TRIGGER_DATE", "to": "触发日期", "apiName": "trigger_date", "type": "DATE"},
            {"from_": "URGENCY_LEVEL", "to": "紧迫等级", "apiName": "urgency_level", "type": "ENUM"},
            {"from_": "ASSIGNED_CHANNEL", "to": "分配渠道", "apiName": "assigned_channel", "type": "FK"},
        ],
    }],
    "lo-script": [{
        "source": "数据中台-全客数据加工 → ADS_QK_FTTR_SCRIPT_TEMPLATE_PT",
        "fields": [
            {"from_": "SCRIPT_ID", "to": "话术ID", "apiName": "script_id", "type": "STRING"},
            {"from_": "SCRIPT_NAME", "to": "名称", "apiName": "script_name", "type": "STRING"},
            {"from_": "SEGMENT_STRUCTURE", "to": "8段式JSON", "apiName": "segment_structure", "type": "JSON"},
            {"from_": "PRODUCT_FAMILY_CODE", "to": "绑定产品族", "apiName": "bound_product_family_ref", "type": "FK"},
            {"from_": "SEGMENT_CODE", "to": "绑定客群", "apiName": "bound_segment_ref", "type": "FK"},
            {"from_": "OBJECTION_TYPES", "to": "目标异议", "apiName": "target_objection_refs", "type": "JSON"},
            {"from_": "MATURITY_LEVEL", "to": "成熟度", "apiName": "maturity_level", "type": "ENUM"},
        ],
    }],
    "lo-touch": [{
        "source": "数据中台-全客数据加工 → ADS_QK_FTTR_TOUCH_LOG_PT",
        "fields": [
            {"from_": "TOUCH_ID", "to": "触达ID", "apiName": "te_id", "type": "STRING"},
            {"from_": "WORKORDER_ID", "to": "关联工单", "apiName": "ref_workorder", "type": "FK"},
            {"from_": "USER_ID", "to": "关联客户", "apiName": "ref_customer", "type": "FK"},
            {"from_": "CHANNEL_CODE", "to": "触达渠道", "apiName": "touch_channel_ref", "type": "FK"},
            {"from_": "RESP_CODE", "to": "触达结果", "apiName": "touch_result", "type": "ENUM"},
            {"from_": "SCRIPT_ID", "to": "使用话术", "apiName": "script_ref", "type": "FK"},
            {"from_": "TOUCH_DT", "to": "触达时间", "apiName": "touch_time", "type": "TIMESTAMP"},
        ],
    }],
    "lo-workorder": [{
        "source": "公众中台-数字化运营 → IOM_D_CONSTRUCTION_INFO / IOM_D_ORDER_ACTION_TIME",
        "fields": [
            {"from_": "WORKORDER_ID", "to": "工单ID", "apiName": "workorder_id", "type": "STRING"},
            {"from_": "USER_ID", "to": "关联客户", "apiName": "customer_ref", "type": "FK"},
            {"from_": "CHANNEL_CODE", "to": "派发渠道", "apiName": "channel_ref", "type": "FK"},
            {"from_": "STAFF_ID", "to": "执行人", "apiName": "staff_ref", "type": "FK"},
            {"from_": "ORDER_STATUS", "to": "工单状态", "apiName": "workorder_status", "type": "ENUM"},
            {"from_": "CREATE_TIME", "to": "创建时间", "apiName": "create_time", "type": "TIMESTAMP"},
        ],
    }],
    "lo-household": [{
        "source": "数据中台-数字沙盘 → DWD_UNIFY_STAND_ADDR_RELATION_PT / ADS_COMMUNITY_3SOURCES_DF_PT_MC",
        "fields": [
            {"from_": "GROUP_ID", "to": "群组ID", "apiName": "group_id", "type": "STRING"},
            {"from_": "MAIN_CARD_USER_ID", "to": "主卡客户", "apiName": "main_card_customer_ref", "type": "FK"},
            {"from_": "MEMBER_USER_IDS", "to": "成员客户", "apiName": "member_customer_refs", "type": "JSON"},
            {"from_": "GROUP_ARPU", "to": "群组ARPU", "apiName": "group_arpu", "type": "DECIMAL"},
            {"from_": "BROADBAND_CNT", "to": "宽带数", "apiName": "broadband_count", "type": "INT"},
            {"from_": "FTTR_PENETRATION", "to": "FTTR渗透率", "apiName": "fttr_penetration", "type": "DECIMAL"},
        ],
    }],
    "lo-kpi": [{
        "source": "数据中台-指标集市/经分应用 → DWA_REVENUE_REPORT_B_ALL / ADS_BI_KPI_DAILY",
        "fields": [
            {"from_": "KPI_VALUE_ID", "to": "度量值ID", "apiName": "kpi_value_id", "type": "STRING"},
            {"from_": "KPI_CODE", "to": "指标编码", "apiName": "kpi_code", "type": "STRING"},
            {"from_": "ACCT_DATE", "to": "账期", "apiName": "acct_date", "type": "DATE"},
            {"from_": "AREA_ID", "to": "地区ID", "apiName": "area_id", "type": "STRING"},
            {"from_": "KPI_VALUE", "to": "指标值", "apiName": "kpi_value", "type": "DECIMAL"},
            {"from_": "M_TB", "to": "同比(%)", "apiName": "m_tb", "type": "DECIMAL"},
            {"from_": "ACHIEVE_RATE", "to": "达成率", "apiName": "achieve_rate", "type": "DECIMAL"},
            {"from_": "IS_ANOMALY", "to": "是否异常", "apiName": "is_anomaly", "type": "BOOLEAN"},
        ],
    }],
}
