#!/usr/bin/env python3
"""
宽带装机退单稽核 — MySQL 建库建表 + 1000条自洽模拟数据
目标: 123.56.188.16:3306  user=bonc  password=bonc123  db=broadband_churn_audit
"""
import random
import uuid
import hashlib
import json
from datetime import datetime, timedelta

import pymysql

DB_CFG = dict(host="123.56.188.16", port=3306, user="bonc", password="bonc123")
DB_NAME = "mnp_risk_warning"
TABLE_PREFIX = "bb_"

random.seed(42)

# ── helpers ──────────────────────────────────────────────

def uid(prefix=""):
    return prefix + hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12]

def rand_dt(start, end):
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=random.randint(0, int(delta)))

def rand_phone():
    return "1" + random.choice("3578") + "".join([str(random.randint(0,9)) for _ in range(9)])

def rand_name():
    surnames = "王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗"
    names = "伟芳娜秀英敏静丽强磊军洋勇艳杰娟涛超明华"
    return random.choice(surnames) + "".join(random.choices(names, k=random.randint(1,2)))

NOW = datetime(2026, 4, 20)
T0 = datetime(2025, 10, 1)

# ── 枚举值 ───────────────────────────────────────────────

PROVINCES = ["北京","上海","广东","江苏","浙江","山东","河南","四川","湖北","湖南","安徽","福建","河北","辽宁","陕西"]
CITIES = {
    "北京":["朝阳区","海淀区","丰台区","东城区"],
    "上海":["浦东新区","徐汇区","静安区","黄浦区"],
    "广东":["广州市","深圳市","东莞市","佛山市"],
    "江苏":["南京市","苏州市","无锡市","常州市"],
    "浙江":["杭州市","宁波市","温州市","嘉兴市"],
}
COMMUNITIES = ["阳光花园","翠苑小区","金色家园","碧水湾","龙湖天街","万科城","绿城花园","保利国际",
               "中海锦城","华润橡树湾","融创壹号","恒大名都","碧桂园","富力城","招商花园城"]

ORDER_STATUS = ["待派单","已派单","施工中","已完工","已退单","已撤单"]
BIZ_TYPE = ["新装","移装","改装","迁移"]
PRODUCT_TYPE = ["FTTH","FTTR","FTTB","ComboAPON"]
CUST_LEVEL = ["普通","二星","四星","五星","六星","SVIP"]
ARREARS = ["正常","欠费停机","历史欠费已缴清"]
ID_CARD = ["已实名","未实名","证件过期","证件信息不全"]
ADDR_LEVEL = ["到室","到楼道","到楼栋","到小区","到村","未覆盖"]
RES_STATUS = ["资源充足","资源紧张","资源不足","建设中","未覆盖"]
AUDIT_STATUS = ["待稽核", "稽核中", "挂起", "完成", "失败"]
AUDIT_WEIGHTS = [15, 5, 20, 50, 10]
L1_CAUSES = ["用户原因","施工原因","资源原因","业务原因"]
L1_WEIGHTS = [30, 25, 25, 20]
L2_MAP = {
    "用户原因": ["用户不想装","联系不上用户","已选友商","实名认证问题","支付/金融问题","用户要求变更"],
    "施工原因": ["入户线问题","施工受阻(物业/房东)","智家人员问题","无法攻克技术问题"],
    "资源原因": ["建设时间长","非无条件受理区域","无资源覆盖","待装无建设计划","资源不足/故障","垄断小区"],
    "业务原因": ["资费疑问","办理条件限制","重复单","未申请业务","受理信息错误","业务规则限制","测试单","渠道权限不足"],
}
DISPATCH_STATUS = ["待接单","已接单","施工中","已完工","已退回","已挂起"]
PENDING_REASON = ["资源不足","建设中","需求待确认","其他"]
CONSTRUCTION_STATUS = ["未发起","已立项","施工中","已完工","已取消"]
CHANNEL_TYPE = ["线上","线下","电话","合作方"]
COMPETITOR = ["移动","电信","广电"]
CONNECT_STATUS = ["已接通","未接通","占线","无人接听"]
EMOTION_TAG = ["平静","焦虑","愤怒","满意","失望","无法判断"]
CALL_TYPE = ["预约确认","施工协调","问题反馈","投诉","其他"]
CALLBACK_PURPOSE = ["信息核实","原因确认","挽回外呼","满意度回访"]
CALLBACK_RESULT = ["信息已补全","客户未接听","客户申请撤单","无法核实"]
TRIGGERED_ACTION = ["工程师培训","网络资源派修","中台回访","挽回外呼","直接归档","人工审核"]
MANUAL_REVIEW_STATUS = ["无需审核","待审核","审核通过","审核驳回","已覆盖"]
PRODUCT_CATEGORY = ["基础宽带","融合套餐","企业宽带","全屋WiFi"]
ADDR_TYPE_APPLICABLE = ["城市","农村","城市,农村"]

# ── 证据/逻辑/动作 枚举 ─────────────────────────────────

EVIDENCE_CODES_NLP = [
    ("E1", "用户主动取消意愿"), ("E2", "用户搬家/不在本地"),
    ("E3", "用户装修中"), ("E4", "用户选择友商"),
    ("E5", "用户资费不满"), ("E6", "用户要求变更"),
    ("E7", "联系不上(ASR确认)"), ("E8", "实名问题(ASR提及)"),
    ("E9", "工程师态度问题"), ("E10", "工程师乱收费"),
    ("E11", "施工受阻(物业)"), ("E12", "入户线问题"),
    ("E13", "技术问题无法开通"), ("E14", "客户情绪愤怒"),
    ("E15", "客户情绪焦虑"), ("E16", "客户满意"),
    ("E17", "工程师推诿"), ("E18", "多次改约"),
    ("E19", "资源不足(ASR提及)"), ("E20", "建设时间长(ASR提及)"),
    ("E21", "回访确认用户取消"), ("E22", "回访确认施工问题"),
    ("E23", "回访确认资源问题"), ("E24", "回访无法联系"),
    ("E25", "回访挽回成功"),
]
EVIDENCE_CODES_RULE = [
    ("E26", "通话失败≥4次且≥2天"), ("E27", "派单延迟>24h"),
    ("E28", "工程师90日退单率>15%"), ("E29", "地址待装库有积压"),
    ("E30", "地址资源状态=不足"), ("E31", "非无条件受理区域"),
    ("E32", "客户黑灰名单"), ("E33", "客户欠费"),
    ("E34", "异网通话记录存在"), ("E35", "人工资源核实结果"),
    ("E36", "竞争对手通话频次高"), ("E37", "回访补全信息"),
]

CAUSE_EVIDENCE_MAP = {
    "用户原因": ["E1","E2","E3","E4","E5","E6","E7","E8","E21","E32","E33","E34","E36"],
    "施工原因": ["E9","E10","E11","E12","E13","E14","E17","E18","E22","E27","E28"],
    "资源原因": ["E19","E20","E23","E29","E30","E31","E35"],
    "业务原因": ["E5","E8","E32","E33"],
}

LOGIC_FUNCTIONS = [
    ("LF-001", "数据采集层", "collect_multi_source_data()"),
    ("LF-002", "NLP证据提取", "extract_nlp_evidence(asr_text)"),
    ("LF-003", "假设树推理", "hypothesis_tree_reasoning(evidence_set)"),
    ("LF-004", "置信度计算", "bayesian_confidence_update(prior, evidence)"),
    ("LF-005", "风险等级判定", "risk_level_judgment(confidence, cause)"),
    ("LF-006", "精调向量修正", "deepseek_refinement(delta<=0.3)"),
    ("LF-007", "路由执行动作", "route_post_archive_action(cause, risk)"),
    ("LF-008", "营销需求识别", "marketing_demand_recognition(transcript)"),
]

ACTION_TYPES = {
    "ACT-001": "受理退单稽核", "ACT-002": "系统自动归档",
    "ACT-003": "转入人工审核", "ACT-004": "人工审核归档",
    "ACT-005": "人工资源核实", "ACT-006": "标记证据异常",
    "ACT-007": "创建补全回访", "ACT-008": "创建强制回访",
    "ACT-009": "回填回访结果", "ACT-010": "写入工程师培训记录",
    "ACT-011": "发起资源派修", "ACT-012": "创建营销外呼记录",
}

CAUSE_ACTION_MAP = {
    "用户原因": ["ACT-008", "ACT-012"],
    "施工原因": ["ACT-010", "ACT-007"],
    "资源原因": ["ACT-011", "ACT-005"],
    "业务原因": ["ACT-007", "ACT-003"],
}

ASSIGNEES = ["张稽核员","李审核员","王主管","赵质检","刘运维","陈回访"]

EXEC_STEPS = {
    "ACT-005": [("发起资源核查", "查询固网资源库"), ("现场核实", "派工程师现场确认"), ("结果回填", "更新资源状态")],
    "ACT-007": [("创建回访任务", "生成中台回访工单"), ("执行回访", "拨打客户电话"), ("结果记录", "回填回访结果")],
    "ACT-008": [("创建强制回访", "生成强制回访工单"), ("执行回访", "拨打客户电话核实"), ("结果确认", "确认退单原因")],
    "ACT-010": [("生成培训记录", "写入工程师培训系统"), ("通知班组长", "发送培训通知")],
    "ACT-011": [("创建派修工单", "生成资源派修工单"), ("派修执行", "工程师现场修复"), ("验收回填", "更新资源状态")],
    "ACT-012": [("创建营销任务", "生成营销外呼记录"), ("执行外呼", "拨打客户挽回电话"), ("结果记录", "回填挽回结果")],
}

# ── 证据/逻辑/动作 枚举 ─────────────────────────────────────
EVIDENCE_CODES_NLP = [
    ("E1", "用户主动取消意愿"), ("E2", "用户搬家/不在本地"),
    ("E3", "用户装修中"), ("E4", "用户选择友商"),
    ("E5", "用户资费不满"), ("E6", "用户要求变更"),
    ("E7", "联系不上(ASR确认)"), ("E8", "实名问题(ASR提及)"),
    ("E9", "工程师态度问题"), ("E10", "工程师乱收费"),
    ("E11", "施工受阻(物业)"), ("E12", "入户线问题"),
    ("E13", "技术问题无法开通"), ("E14", "客户情绪愤怒"),
    ("E15", "客户情绪焦虑"), ("E16", "客户满意"),
    ("E17", "工程师推诿"), ("E18", "多次改约"),
    ("E19", "资源不足(ASR提及)"), ("E20", "建设时间长(ASR提及)"),
    ("E21", "回访确认用户取消"), ("E22", "回访确认施工问题"),
    ("E23", "回访确认资源问题"), ("E24", "回访无法联系"),
    ("E25", "回访挽回成功"),
]
EVIDENCE_CODES_RULE = [
    ("E26", "通话失败≥4次且≥2天"), ("E27", "派单延迟>24h"),
    ("E28", "工程师90日退单率>15%"), ("E29", "地址待装库有积压"),
    ("E30", "地址资源状态=不足"), ("E31", "非无条件受理区域"),
    ("E32", "客户黑灰名单"), ("E33", "客户欠费"),
    ("E34", "异网通话记录存在"), ("E35", "人工资源核实结果"),
    ("E36", "竞争对手通话频次高"), ("E37", "回访补全信息"),
]
CAUSE_EVIDENCE_MAP = {
    "用户原因": ["E1","E2","E3","E4","E5","E6","E7","E8","E21","E32","E33","E34","E36"],
    "施工原因": ["E9","E10","E11","E12","E13","E14","E17","E18","E22","E27","E28"],
    "资源原因": ["E19","E20","E23","E29","E30","E31","E35"],
    "业务原因": ["E5","E8","E32","E33"],
}

# ASR 关键词模板 — 按退单原因分类
ASR_TEMPLATES = {
    "用户不想装": ["客户说暂时不装了","用户表示不需要宽带了","客户说要搬家，不办了","用户说在装修，等装修好再说","客户说暂时不在本地"],
    "联系不上用户": ["多次拨打无人接听","客户电话暂时无法接通","号码已停机","拨打提示空号","客户电话一直关机"],
    "已选友商": ["客户说已经办理了移动宽带","用户表示已办理电信宽带","客户说邻居推荐了电信"],
    "实名认证问题": ["客户身份证丢了，无法实名","证件照模糊不清","用户未满18岁","身份证没磁了需要补办"],
    "支付/金融问题": ["客户说费用太贵了","用户表示月租太高","安装费用问题","客户说调测费不合理"],
    "用户要求变更": ["客户要求更换套餐","用户说要自备设备还没到","客户要求改地址"],
    "入户线问题": ["暗线不通需要重新布线","孔堵死了打不了洞","装修原因线路不通","需要打孔客户不同意明线"],
    "施工受阻(物业/房东)": ["物业不让施工","房东不同意打孔","邻居不让过线","物业锁了机房进不去"],
    "智家人员问题": ["工程师说没空改约了","师傅态度不好客户投诉","工程师乱收费","一直没人联系客户"],
    "无法攻克技术问题": ["光猫无法注册","ONU设备故障","光衰过大无法开通","终端设备兼容问题"],
    "建设时间长": ["需要等待建设，大概要30天","资源建设中预计2个月","扩容中暂时装不通","客户不愿意等太久"],
    "非无条件受理区域": ["该区域不是无条件受理","需要先确认资源再受理","地址不在覆盖范围"],
    "无资源覆盖": ["该地址无宽带资源覆盖","太偏远没有覆盖","没有光纤资源"],
    "待装无建设计划": ["待装库里没有建设计划","暂无扩容计划","资源不足且无建设排期"],
    "资源不足/故障": ["分光器端口满了","OLT设备故障","光缆中断维修中"],
    "垄断小区": ["该小区被其他运营商垄断","物业只允许一家运营商"],
    "资费疑问": ["客户觉得费用不透明","月租和宣传不一致","安装费问题"],
    "办理条件限制": ["客户在黑名单无法办理","用户有欠费不能开户","身份证过期无法办理"],
    "重复单": ["同一用户重复下单","已有在途工单","渠道重复受理"],
    "未申请业务": ["客户说没有申请过宽带","不是本人下的单","没有订过这个业务"],
    "受理信息错误": ["地址录入错误","电话号码不是客户的","产品信息有误需重新下单"],
    "业务规则限制": ["系统报错无法受理","互斥产品冲突","用户状态异常"],
    "测试单": ["这是测试工单","内部测试订单"],
    "渠道权限不足": ["该渠道无权受理此产品","渠道权限不够"],
}

# ── DDL ──────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS bb_channel (
  channel_id VARCHAR(20) PRIMARY KEY,
  channel_name VARCHAR(100),
  channel_type VARCHAR(20),
  hist_churn_rate DECIMAL(6,4),
  is_self_operated TINYINT(1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_product (
  product_id VARCHAR(20) PRIMARY KEY,
  product_name VARCHAR(100),
  bandwidth_mbps INT,
  monthly_price DECIMAL(8,2),
  product_category VARCHAR(30),
  applicable_address_type VARCHAR(30)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_customer (
  customer_id VARCHAR(20) PRIMARY KEY,
  customer_name VARCHAR(50),
  contact_phone VARCHAR(20),
  customer_level VARCHAR(10),
  network_age INT,
  hist_complaint_count INT DEFAULT 0,
  hist_churn_count INT DEFAULT 0,
  is_blacklist TINYINT(1) DEFAULT 0,
  arrears_status VARCHAR(20) DEFAULT '正常',
  id_card_status VARCHAR(20) DEFAULT '已实名'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_engineer (
  engineer_id VARCHAR(20) PRIMARY KEY,
  engineer_name VARCHAR(50),
  phone VARCHAR(20),
  team_id VARCHAR(20),
  team_name VARCHAR(50),
  is_team_leader TINYINT(1) DEFAULT 0,
  skill_tags VARCHAR(200),
  churn_rate_90d DECIMAL(6,4),
  on_time_rate_90d DECIMAL(6,4),
  optical_qualify_rate DECIMAL(6,4),
  avg_satisfaction DECIMAL(3,1),
  training_status TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_address (
  address_id VARCHAR(20) PRIMARY KEY,
  standard_address_name VARCHAR(300),
  address_level VARCHAR(20),
  is_unconditional_accept TINYINT(1) DEFAULT 1,
  open_time_limit_days INT DEFAULT 7,
  resource_status VARCHAR(20) DEFAULT '资源充足',
  hist_churn_rate DECIMAL(6,4),
  community_name VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_install_order (
  order_no VARCHAR(30) PRIMARY KEY,
  cust_id VARCHAR(20),
  engineer_id VARCHAR(20),
  accept_time DATETIME,
  order_status VARCHAR(20),
  biz_type VARCHAR(10),
  product_type VARCHAR(20),
  product_id VARCHAR(20),
  product_name VARCHAR(100),
  channel_id VARCHAR(20),
  install_address_id VARCHAR(20),
  install_address VARCHAR(300),
  finish_time DATETIME,
  speed_test_result DECIMAL(6,1),
  optical_power_db DECIMAL(5,1),
  satisfaction_score INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_install_churn (
  churn_id VARCHAR(30) PRIMARY KEY,
  related_order_no VARCHAR(30),
  churn_time DATETIME,
  churn_reason_text VARCHAR(500),
  churn_category_l1 VARCHAR(20),
  churn_category_l2 VARCHAR(50),
  audit_status VARCHAR(20) DEFAULT '待稽核',
  audit_start_time DATETIME,
  escalate_time DATETIME,
  escalate_reason VARCHAR(50),
  root_cause_code VARCHAR(10),
  root_cause_level_one VARCHAR(20),
  root_cause_level_two VARCHAR(50),
  root_cause_confidence DECIMAL(5,4),
  secondary_cause_label VARCHAR(50),
  evidence_chain_summary TEXT,
  reasoning_path_snapshot TEXT,
  triggered_action_type VARCHAR(30),
  manual_review_status VARCHAR(20) DEFAULT '无需审核',
  manual_override_label VARCHAR(50),
  archive_time DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_dispatch_record (
  dispatch_id VARCHAR(30) PRIMARY KEY,
  related_order_no VARCHAR(30),
  engineer_id VARCHAR(20),
  dispatch_time DATETIME,
  dispatch_status VARCHAR(20),
  book_time DATETIME,
  arrive_time DATETIME,
  finish_time DATETIME,
  wait_duration_minutes INT,
  late_duration_minutes INT,
  transfer_count INT DEFAULT 0,
  suspend_reason VARCHAR(200),
  appointment_change_count INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_pending_pool (
  record_id VARCHAR(30) PRIMARY KEY,
  related_address_id VARCHAR(20),
  order_no VARCHAR(30),
  entry_time DATETIME,
  pending_reason VARCHAR(30),
  current_backlog_count INT DEFAULT 1,
  backlog_duration_days INT DEFAULT 0,
  hist_backlog_frequency INT DEFAULT 0,
  construction_status VARCHAR(20) DEFAULT '未发起'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_competitor_call (
  call_id VARCHAR(30) PRIMARY KEY,
  customer_id VARCHAR(20),
  customer_phone VARCHAR(20),
  called_phone VARCHAR(20),
  call_time DATETIME,
  competitor_type VARCHAR(10)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_evidence (
  evidence_id VARCHAR(30) PRIMARY KEY,
  churn_id VARCHAR(30) NOT NULL,
  evidence_code VARCHAR(10) NOT NULL,
  evidence_type ENUM('nlp','rule','manual') NOT NULL,
  source_type VARCHAR(30),
  source_id VARCHAR(30),
  content TEXT,
  raw_text TEXT,
  hit TINYINT(1) DEFAULT 0,
  confidence DECIMAL(5,4) DEFAULT NULL,
  extracted_at DATETIME DEFAULT NOW(),
  INDEX idx_ev_churn (churn_id),
  INDEX idx_ev_code (evidence_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_logic_hit (
  hit_id VARCHAR(30) PRIMARY KEY,
  churn_id VARCHAR(30) NOT NULL,
  evidence_id VARCHAR(30),
  logic_function_id VARCHAR(10) NOT NULL,
  logic_function_name VARCHAR(50),
  rule_expression TEXT,
  hit_result VARCHAR(20),
  confidence_delta DECIMAL(5,4) DEFAULT 0,
  executed_at DATETIME DEFAULT NOW(),
  INDEX idx_lh_churn (churn_id),
  INDEX idx_lh_lf (logic_function_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_audit_action (
  action_id VARCHAR(30) PRIMARY KEY,
  churn_id VARCHAR(30) NOT NULL,
  action_type_code VARCHAR(10) NOT NULL,
  action_name VARCHAR(50) NOT NULL,
  description TEXT,
  priority ENUM('high','medium','low') DEFAULT 'medium',
  status ENUM('pending_approval','approved','rejected','executing','completed','failed') DEFAULT 'pending_approval',
  assignee VARCHAR(50),
  created_at DATETIME DEFAULT NOW(),
  approved_at DATETIME,
  approved_by VARCHAR(50),
  rejected_at DATETIME,
  rejected_by VARCHAR(50),
  reject_reason VARCHAR(500),
  params_json JSON,
  INDEX idx_aa_churn (churn_id),
  INDEX idx_aa_status (status),
  INDEX idx_aa_type (action_type_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_action_execution (
  execution_id VARCHAR(30) PRIMARY KEY,
  action_id VARCHAR(30) NOT NULL,
  step_name VARCHAR(50),
  status ENUM('executing','completed','failed') DEFAULT 'executing',
  result_text TEXT,
  writeback_content TEXT,
  started_at DATETIME DEFAULT NOW(),
  completed_at DATETIME,
  executor VARCHAR(50),
  log_text TEXT,
  INDEX idx_ae_action (action_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_audit_trail (
  trail_id VARCHAR(30) PRIMARY KEY,
  churn_id VARCHAR(30) NOT NULL,
  event_type VARCHAR(30) NOT NULL,
  event_detail TEXT,
  operator VARCHAR(50) DEFAULT 'system',
  created_at DATETIME DEFAULT NOW(),
  INDEX idx_at_churn (churn_id),
  INDEX idx_at_type (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_engineer_call (
  call_id VARCHAR(30) PRIMARY KEY,
  related_order_no VARCHAR(30),
  engineer_id VARCHAR(20),
  customer_phone VARCHAR(20),
  call_start_time DATETIME,
  call_end_time DATETIME,
  duration_seconds INT,
  connect_status VARCHAR(20),
  asr_text TEXT,
  customer_emotion_tag VARCHAR(20),
  call_type VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bb_callback_call (
  call_id VARCHAR(30) PRIMARY KEY,
  related_order_no VARCHAR(30),
  related_customer_id VARCHAR(20),
  call_start_time DATETIME,
  call_end_time DATETIME,
  duration_seconds INT,
  connect_status VARCHAR(20),
  asr_text TEXT,
  callback_purpose VARCHAR(30),
  callback_result VARCHAR(30),
  supplement_info VARCHAR(500)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# ── 数据生成 ─────────────────────────────────────────────

def generate_all():
    # 1. 渠道 (10)
    channels = []
    ch_names = ["联通APP","联通营业厅","10010热线","京东旗舰店","天猫旗舰店",
                "社区经理","校园渠道","企业直销","合作代理商A","合作代理商B"]
    for i, name in enumerate(ch_names):
        channels.append({
            "channel_id": f"CH{i+1:03d}",
            "channel_name": name,
            "channel_type": CHANNEL_TYPE[i % len(CHANNEL_TYPE)],
            "hist_churn_rate": round(random.uniform(0.02, 0.18), 4),
            "is_self_operated": 1 if i < 6 else 0,
        })

    # 2. 产品 (20)
    products = []
    bw_list = [100, 200, 300, 500, 1000]
    for i in range(20):
        bw = random.choice(bw_list)
        cat = random.choice(PRODUCT_CATEGORY)
        products.append({
            "product_id": f"PRD{i+1:03d}",
            "product_name": f"{cat}-{bw}M-{'城市' if i%2==0 else '农村'}版",
            "bandwidth_mbps": bw,
            "monthly_price": round(random.uniform(39, 299), 2),
            "product_category": cat,
            "applicable_address_type": random.choice(ADDR_TYPE_APPLICABLE),
        })

    # 3. 客户 (800)
    customers = []
    for i in range(800):
        customers.append({
            "customer_id": f"CUST{i+1:06d}",
            "customer_name": rand_name(),
            "contact_phone": rand_phone(),
            "customer_level": random.choices(CUST_LEVEL, weights=[40,20,15,12,8,5])[0],
            "network_age": random.randint(1, 180),
            "hist_complaint_count": random.choices([0,1,2,3,4,5], weights=[50,20,15,8,5,2])[0],
            "hist_churn_count": random.choices([0,1,2,3], weights=[60,25,10,5])[0],
            "is_blacklist": 1 if random.random() < 0.03 else 0,
            "arrears_status": random.choices(ARREARS, weights=[85,10,5])[0],
            "id_card_status": random.choices(ID_CARD, weights=[80,10,5,5])[0],
        })

    # 4. 工程师 (50)
    engineers = []
    teams = [(f"T{j+1:02d}", f"装维{j+1}班组") for j in range(10)]
    skills = ["FTTH安装","FTTR组网","光纤熔接","智家设备调试","网络测速"]
    for i in range(50):
        t = teams[i % len(teams)]
        engineers.append({
            "engineer_id": f"ENG{i+1:04d}",
            "engineer_name": rand_name(),
            "phone": rand_phone(),
            "team_id": t[0],
            "team_name": t[1],
            "is_team_leader": 1 if i % 5 == 0 else 0,
            "skill_tags": ",".join(random.sample(skills, k=random.randint(2,4))),
            "churn_rate_90d": round(random.uniform(0.01, 0.25), 4),
            "on_time_rate_90d": round(random.uniform(0.70, 0.99), 4),
            "optical_qualify_rate": round(random.uniform(0.75, 0.99), 4),
            "avg_satisfaction": round(random.uniform(3.0, 5.0), 1),
            "training_status": "[]",
        })

    # 5. 地址 (500)
    addresses = []
    for i in range(500):
        prov = random.choice(PROVINCES)
        city = random.choice(CITIES.get(prov, [prov + "市"]))
        comm = random.choice(COMMUNITIES)
        al = random.choices(ADDR_LEVEL, weights=[40,15,15,15,10,5])[0]
        rs = "未覆盖" if al == "未覆盖" else random.choices(RES_STATUS[:4], weights=[50,20,20,10])[0]
        addresses.append({
            "address_id": f"ADDR{i+1:05d}",
            "standard_address_name": f"{prov}{city}{comm}{random.randint(1,30)}栋{random.randint(1,6)}单元{random.randint(101,2505)}室",
            "address_level": al,
            "is_unconditional_accept": 0 if al in ("未覆盖","到村") else (1 if random.random() < 0.7 else 0),
            "open_time_limit_days": random.choice([3,5,7,10,15]),
            "resource_status": rs,
            "hist_churn_rate": round(random.uniform(0.0, 0.3), 4),
            "community_name": comm,
        })

    # 6. 工单 + 退单 + 派单 + 通话 (1000)
    orders, churns, dispatches = [], [], []
    eng_calls, cb_calls, comp_calls = [], [], []
    pending_pool = []

    for i in range(1000):
        ono = f"WO{20250000+i+1}"
        cust = random.choice(customers)
        eng = random.choice(engineers)
        addr = random.choice(addresses)
        prod = random.choice(products)
        ch = random.choice(channels)
        accept = rand_dt(T0, NOW - timedelta(days=3))
        finish = accept + timedelta(hours=random.randint(2, 72*24)//24, minutes=random.randint(0,59))
        churn_time = finish + timedelta(hours=random.randint(1, 48))
        if churn_time > NOW:
            churn_time = NOW - timedelta(hours=random.randint(1, 48))

        orders.append({
            "order_no": ono,
            "cust_id": cust["customer_id"],
            "engineer_id": eng["engineer_id"],
            "accept_time": accept.strftime("%Y-%m-%d %H:%M:%S"),
            "order_status": "已退单",
            "biz_type": random.choices(BIZ_TYPE, weights=[60,20,10,10])[0],
            "product_type": random.choice(PRODUCT_TYPE),
            "product_id": prod["product_id"],
            "product_name": prod["product_name"],
            "channel_id": ch["channel_id"],
            "install_address_id": addr["address_id"],
            "install_address": addr["standard_address_name"],
            "finish_time": finish.strftime("%Y-%m-%d %H:%M:%S") if random.random() < 0.3 else None,
            "speed_test_result": round(random.uniform(50, 1000), 1) if random.random() < 0.3 else None,
            "optical_power_db": round(random.uniform(-27, -8), 1) if random.random() < 0.3 else None,
            "satisfaction_score": random.randint(1, 5) if random.random() < 0.3 else None,
        })

        # 退单
        a_status = random.choices(AUDIT_STATUS, weights=AUDIT_WEIGHTS)[0]
        l1 = random.choices(L1_CAUSES, weights=L1_WEIGHTS)[0]
        l2 = random.choice(L2_MAP[l1])

        if a_status == "已归档":
            conf = round(random.uniform(0.60, 1.0), 4)
            archive_t = churn_time + timedelta(hours=random.randint(1, 72))
            m_status = random.choice(["无需审核","审核通过","已覆盖"])
            trig = random.choice(TRIGGERED_ACTION)
        elif a_status == "待人工审核":
            conf = round(random.uniform(0.20, 0.59), 4)
            archive_t = None
            m_status = "待审核"
            trig = "人工审核"
        elif a_status in ("待补全回访","强制回访待核实"):
            conf = round(random.uniform(0.60, 0.84), 4)
            archive_t = None
            m_status = "无需审核"
            trig = "中台回访"
        elif a_status == "推理中":
            conf = None
            archive_t = None
            m_status = "无需审核"
            trig = None
        else:
            conf = None
            archive_t = None
            m_status = "无需审核"
            trig = None

        root_code = f"{l1[0]}{L2_MAP[l1].index(l2)+1}" if conf else None
        sec_l1 = random.choice([x for x in L1_CAUSES if x != l1])
        sec_l2 = random.choice(L2_MAP[sec_l1]) if conf else None

        asr_samples = ASR_TEMPLATES.get(l2, ["退单原因待确认"])
        evidence_summary = f"[E-{random.randint(1,37)}] {random.choice(asr_samples)}" if conf else None

        audit_start = churn_time + timedelta(minutes=random.randint(5, 120)) if a_status != "待稽核" else None
        esc_time = audit_start + timedelta(hours=random.randint(1,24)) if a_status == "待人工审核" and audit_start else None
        esc_reason = "置信度不足" if a_status == "待人工审核" else None

        churns.append({
            "churn_id": f"TD{20250000+i+1}",
            "related_order_no": ono,
            "churn_time": churn_time.strftime("%Y-%m-%d %H:%M:%S"),
            "churn_reason_text": random.choice(asr_samples),
            "churn_category_l1": l1,
            "churn_category_l2": l2,
            "audit_status": a_status,
            "audit_start_time": audit_start.strftime("%Y-%m-%d %H:%M:%S") if audit_start else None,
            "escalate_time": esc_time.strftime("%Y-%m-%d %H:%M:%S") if esc_time else None,
            "escalate_reason": esc_reason,
            "root_cause_code": root_code,
            "root_cause_level_one": l1 if conf else None,
            "root_cause_level_two": l2 if conf else None,
            "root_cause_confidence": conf,
            "secondary_cause_label": sec_l2,
            "evidence_chain_summary": evidence_summary,
            "reasoning_path_snapshot": None,
            "triggered_action_type": trig,
            "manual_review_status": m_status,
            "manual_override_label": None,
            "archive_time": archive_t.strftime("%Y-%m-%d %H:%M:%S") if archive_t else None,
        })

        # 派单
        disp_time = accept + timedelta(minutes=random.randint(10, 480))
        book_time = disp_time + timedelta(hours=random.randint(1, 48))
        arrive_time = book_time + timedelta(minutes=random.randint(-30, 120))
        dispatches.append({
            "dispatch_id": f"DP{20250000+i+1}",
            "related_order_no": ono,
            "engineer_id": eng["engineer_id"],
            "dispatch_time": disp_time.strftime("%Y-%m-%d %H:%M:%S"),
            "dispatch_status": random.choice(DISPATCH_STATUS),
            "book_time": book_time.strftime("%Y-%m-%d %H:%M:%S"),
            "arrive_time": arrive_time.strftime("%Y-%m-%d %H:%M:%S"),
            "finish_time": orders[-1]["finish_time"],
            "wait_duration_minutes": int((disp_time - accept).total_seconds() / 60),
            "late_duration_minutes": int((arrive_time - book_time).total_seconds() / 60),
            "transfer_count": random.choices([0,1,2,3], weights=[60,25,10,5])[0],
            "suspend_reason": random.choice(["","","","资源不足","客户改约","物业阻挡"]),
            "appointment_change_count": random.choices([0,1,2,3], weights=[50,30,15,5])[0],
        })

        # 工程师通话 (80% 的工单有)
        if random.random() < 0.8:
            call_t = accept + timedelta(hours=random.randint(1, 72))
            dur = random.randint(15, 600)
            eng_calls.append({
                "call_id": f"EC{uid()}",
                "related_order_no": ono,
                "engineer_id": eng["engineer_id"],
                "customer_phone": cust["contact_phone"],
                "call_start_time": call_t.strftime("%Y-%m-%d %H:%M:%S"),
                "call_end_time": (call_t + timedelta(seconds=dur)).strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": dur,
                "connect_status": random.choices(CONNECT_STATUS, weights=[70,15,5,10])[0],
                "asr_text": random.choice(ASR_TEMPLATES.get(l2, ["通话内容待转写"])),
                "customer_emotion_tag": random.choice(EMOTION_TAG),
                "call_type": random.choice(CALL_TYPE),
            })

        # 回访通话 (40% 的工单有)
        if random.random() < 0.4:
            call_t = churn_time + timedelta(hours=random.randint(1, 48))
            dur = random.randint(30, 300)
            cb_calls.append({
                "call_id": f"CB{uid()}",
                "related_order_no": ono,
                "related_customer_id": cust["customer_id"],
                "call_start_time": call_t.strftime("%Y-%m-%d %H:%M:%S"),
                "call_end_time": (call_t + timedelta(seconds=dur)).strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": dur,
                "connect_status": random.choices(CONNECT_STATUS, weights=[65,20,5,10])[0],
                "asr_text": random.choice(ASR_TEMPLATES.get(l2, ["回访内容待转写"])),
                "callback_purpose": random.choice(CALLBACK_PURPOSE),
                "callback_result": random.choice(CALLBACK_RESULT),
                "supplement_info": "" if random.random() < 0.5 else f"客户补充说明：{random.choice(asr_samples)}",
            })

        # 异网通话 (30% 的用户原因工单有)
        if l1 == "用户原因" and random.random() < 0.5:
            call_t = churn_time - timedelta(hours=random.randint(1, 72))
            comp_calls.append({
                "call_id": f"CC{uid()}",
                "customer_id": cust["customer_id"],
                "customer_phone": cust["contact_phone"],
                "called_phone": random.choice(["10086","10000","10096","10010"]),
                "call_time": call_t.strftime("%Y-%m-%d %H:%M:%S"),
                "competitor_type": random.choice(COMPETITOR),
            })

        # 待装池 (资源原因的工单有)
        if l1 == "资源原因" and random.random() < 0.7:
            pending_pool.append({
                "record_id": f"PP{uid()}",
                "related_address_id": addr["address_id"],
                "order_no": ono,
                "entry_time": accept.strftime("%Y-%m-%d %H:%M:%S"),
                "pending_reason": random.choice(PENDING_REASON[:2]),
                "current_backlog_count": random.randint(1, 30),
                "backlog_duration_days": random.randint(1, 90),
                "hist_backlog_frequency": random.randint(0, 10),
                "construction_status": random.choice(CONSTRUCTION_STATUS),
            })

    return channels, products, customers, engineers, addresses, orders, churns, dispatches, eng_calls, cb_calls, comp_calls, pending_pool


def generate_evidence_and_actions(churns):
    """为每条churn生成证据、逻辑命中、动作、执行记录、审计追踪"""
    all_evidence, all_logic_hits, all_actions, all_executions, all_trail = [], [], [], [], []
    ev_code_map = {c: d for c, d in EVIDENCE_CODES_NLP + EVIDENCE_CODES_RULE}

    for ch in churns:
        cid = ch["churn_id"]
        l1 = ch["churn_category_l1"]
        a_status = ch["audit_status"]
        conf = ch["root_cause_confidence"]
        churn_time = ch["churn_time"]

        # ── 证据 ──
        preferred = CAUSE_EVIDENCE_MAP.get(l1, [])
        other_codes = [c for c, _ in EVIDENCE_CODES_NLP + EVIDENCE_CODES_RULE if c not in preferred]
        n_ev = random.randint(5, 15)
        n_hit = random.randint(2, min(n_ev, len(preferred)))
        hit_codes = random.sample(preferred, min(n_hit, len(preferred)))
        miss_codes = random.sample(other_codes, min(n_ev - len(hit_codes), len(other_codes)))
        ev_ids = []

        for code in hit_codes + miss_codes:
            eid = f"EV{uid()}"
            ev_ids.append(eid)
            is_nlp = code in [c for c, _ in EVIDENCE_CODES_NLP]
            src_types = ["engineer_call", "callback_call"] if is_nlp else ["order", "address", "dispatch", "pending_pool", "competitor_call"]
            all_evidence.append({
                "evidence_id": eid,
                "churn_id": cid,
                "evidence_code": code,
                "evidence_type": "nlp" if is_nlp else "rule",
                "source_type": random.choice(src_types),
                "source_id": uid("SRC"),
                "content": ev_code_map.get(code, ""),
                "raw_text": random.choice(list(ASR_TEMPLATES.values())[0]) if is_nlp else None,
                "hit": 1 if code in hit_codes else 0,
                "confidence": round(random.uniform(0.6, 0.99), 4) if code in hit_codes else round(random.uniform(0.05, 0.3), 4),
                "extracted_at": churn_time,
            })

        # ── 审计追踪: 证据提取 ──
        all_trail.append({
            "trail_id": f"TRL{uid()}", "churn_id": cid,
            "event_type": "evidence_extracted",
            "event_detail": f"提取{len(hit_codes + miss_codes)}条证据，命中{len(hit_codes)}条",
            "operator": "system", "created_at": churn_time,
        })

        # ── 逻辑函数命中 ──
        if a_status != "待稽核":
            lf_list = [("LF-001", "数据采集层")]
            if ev_ids:
                lf_list.append(("LF-002", "NLP证据提取"))
            if conf is not None:
                lf_list += [("LF-003", "假设树推理"), ("LF-004", "置信度计算"), ("LF-005", "风险等级判定")]
            if conf and conf >= 0.85:
                lf_list.append(("LF-006", "精调向量修正"))
            if a_status == "已归档":
                lf_list.append(("LF-007", "路由执行动作"))

            for lf_id, lf_name in lf_list:
                linked_ev = random.choice(ev_ids) if ev_ids else None
                lf_full = next((expr for fid, _, expr in LOGIC_FUNCTIONS if fid == lf_id), "")
                all_logic_hits.append({
                    "hit_id": f"LH{uid()}", "churn_id": cid,
                    "evidence_id": linked_ev,
                    "logic_function_id": lf_id,
                    "logic_function_name": lf_name,
                    "rule_expression": lf_full,
                    "hit_result": "hit" if random.random() < 0.8 else "partial",
                    "confidence_delta": round(random.uniform(-0.1, 0.2), 4),
                    "executed_at": churn_time,
                })

            all_trail.append({
                "trail_id": f"TRL{uid()}", "churn_id": cid,
                "event_type": "logic_hit",
                "event_detail": f"执行{len(lf_list)}个逻辑函数",
                "operator": "system", "created_at": churn_time,
            })

        # ── 稽核动作（对齐 poc-service-api 待办状态机）──
        actions_for_churn = []
        if a_status == "完成":
            # 已完成的退单：生成已反馈的待办
            cause_todos = {
                "用户原因": [("followup_call", "中台外呼回访 — 退单原因核实")],
                "施工原因": [("followup_call", "中台外呼回访 — 退单原因核实")],
                "资源原因": [("resource_check", "地址网络资源核实")],
                "业务原因": [("followup_call", "中台外呼回访 — 退单原因核实")],
            }
            for todo_type, todo_name in cause_todos.get(l1, []):
                actions_for_churn.append((todo_type, todo_name, "feedback_submitted"))
            if random.random() < 0.3:
                actions_for_churn.append(("secondary_marketing", "二次营销 — 客户挽留", "feedback_submitted"))
        elif a_status == "挂起":
            # 挂起的退单：生成待确认或待反馈的待办
            todo_choices = [
                ("resource_check", "地址网络资源核实"),
                ("followup_call", "中台外呼回访 — 退单原因核实"),
            ]
            todo_type, todo_name = random.choice(todo_choices)
            todo_status = random.choice(["pending_confirm", "pending_feedback"])
            actions_for_churn.append((todo_type, todo_name, todo_status))
            if random.random() < 0.3:
                actions_for_churn.append(("secondary_marketing", "二次营销 — 客户挽留", "pending_confirm"))

        for todo_type, todo_name, act_status in actions_for_churn:
            aid = f"ACT{uid()}"
            assignee = random.choice(ASSIGNEES)
            created = churn_time
            approved_at = None
            approved_by = None
            if act_status in ("pending_feedback", "feedback_submitted"):
                approved_at = churn_time
                approved_by = random.choice(ASSIGNEES)

            feedback_data = None
            feedback_time = None
            if act_status == "feedback_submitted":
                feedback_time = churn_time
                if todo_type == "resource_check":
                    feedback_data = json.dumps({"type": "resource_check", "value": random.choice(["有资源", "无资源"]), "text": "现场核实完成"}, ensure_ascii=False)
                elif todo_type == "followup_call":
                    feedback_data = json.dumps({"type": "followup_call", "value": random.choice(["确认用户原因", "实际为施工原因", "实际为资源原因"]), "text": "回访完成"}, ensure_ascii=False)

            all_actions.append({
                "action_id": aid, "churn_id": cid,
                "action_type_code": todo_type,
                "todo_type": todo_type,
                "action_name": todo_name,
                "description": f"针对退单{cid}执行{todo_name}",
                "priority": random.choice(["high", "medium", "low"]),
                "status": act_status,
                "assignee": assignee,
                "created_at": created,
                "approved_at": approved_at,
                "approved_by": approved_by,
                "rejected_at": None, "rejected_by": None, "reject_reason": None,
                "params_json": None,
                "feedback_data": feedback_data,
                "feedback_time": feedback_time,
            })

            all_trail.append({
                "trail_id": f"TRL{uid()}", "churn_id": cid,
                "event_type": "action_created",
                "event_detail": f"创建待办 {todo_name}",
                "operator": "system", "created_at": created,
            })

            if act_status in ("pending_feedback", "feedback_submitted"):
                all_trail.append({
                    "trail_id": f"TRL{uid()}", "churn_id": cid,
                    "event_type": "action_confirmed",
                    "event_detail": f"确认接受 {todo_name}",
                    "operator": approved_by, "created_at": approved_at,
                })

            if act_status == "feedback_submitted":
                all_trail.append({
                    "trail_id": f"TRL{uid()}", "churn_id": cid,
                    "event_type": "action_feedback",
                    "event_detail": f"提交反馈 {todo_name}",
                    "operator": assignee, "created_at": feedback_time,
                })

        # ── 状态变更追踪 ──
        all_trail.append({
            "trail_id": f"TRL{uid()}", "churn_id": cid,
            "event_type": "status_changed",
            "event_detail": f"稽核状态变更为: {a_status}",
            "operator": "system", "created_at": churn_time,
        })

    return all_evidence, all_logic_hits, all_actions, all_executions, all_trail

# ── 批量插入 ─────────────────────────────────────────────

def batch_insert(cur, table, rows, batch=200):
    if not rows:
        return
    cols = list(rows[0].keys())
    placeholders = ",".join(["%s"] * len(cols))
    col_str = ",".join(cols)
    sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})"
    for start in range(0, len(rows), batch):
        chunk = rows[start:start+batch]
        vals = [tuple(r[c] for c in cols) for r in chunk]
        cur.executemany(sql, vals)
    print(f"  {table}: {len(rows)} rows")


def main():
    print("=== 宽带退单稽核数据初始化 ===")
    print(f"目标: {DB_CFG['host']}:{DB_CFG['port']} / {DB_NAME}")

    # 连接并建库
    conn = pymysql.connect(**DB_CFG, charset="utf8mb4")
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE `{DB_NAME}`")
    conn.commit()
    print("数据库已创建")

    # 建表（先删旧表）
    tables = ["bb_audit_trail","bb_action_execution","bb_audit_action","bb_logic_hit","bb_evidence",
              "bb_callback_call","bb_engineer_call","bb_competitor_call","bb_pending_pool",
              "bb_dispatch_record","bb_install_churn","bb_install_order",
              "bb_address","bb_engineer","bb_customer","bb_product","bb_channel"]
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS `{t}`")
    conn.commit()

    for stmt in DDL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    conn.commit()
    print("表结构已创建")

    # 生成数据
    print("生成模拟数据...")
    (channels, products, customers, engineers, addresses,
     orders, churns, dispatches, eng_calls, cb_calls, comp_calls, pending_pool) = generate_all()

    # 插入
    print("插入数据...")
    batch_insert(cur, "bb_channel", channels)
    batch_insert(cur, "bb_product", products)
    batch_insert(cur, "bb_customer", customers)
    batch_insert(cur, "bb_engineer", engineers)
    batch_insert(cur, "bb_address", addresses)
    batch_insert(cur, "bb_install_order", orders)
    batch_insert(cur, "bb_install_churn", churns)
    batch_insert(cur, "bb_dispatch_record", dispatches)
    batch_insert(cur, "bb_engineer_call", eng_calls)
    batch_insert(cur, "bb_callback_call", cb_calls)
    batch_insert(cur, "bb_competitor_call", comp_calls)
    batch_insert(cur, "bb_pending_pool", pending_pool)
    conn.commit()

    # 生成证据/逻辑/动作/执行/追踪数据
    print("生成证据与动作数据...")
    evidence, logic_hits, actions, executions, trail = generate_evidence_and_actions(churns)
    batch_insert(cur, "bb_evidence", evidence)
    batch_insert(cur, "bb_logic_hit", logic_hits)
    batch_insert(cur, "bb_audit_action", actions)
    batch_insert(cur, "bb_action_execution", executions)
    batch_insert(cur, "bb_audit_trail", trail)
    conn.commit()

    # 统计
    print("\n=== 数据统计 ===")
    for t in ["bb_channel","bb_product","bb_customer","bb_engineer","bb_address",
              "bb_install_order","bb_install_churn","bb_dispatch_record",
              "bb_engineer_call","bb_callback_call","bb_competitor_call","bb_pending_pool",
              "bb_evidence","bb_logic_hit","bb_audit_action","bb_action_execution","bb_audit_trail"]:
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        print(f"  {t}: {cur.fetchone()[0]}")

    cur.close()
    conn.close()
    print("\n完成!")


if __name__ == "__main__":
    main()
