"""初始化本体种子数据（SQLite + Neo4j）"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.entity import OntologyEntity, EntityAttribute
from app.models.relation import EntityRelation
from app.models.rule import BusinessRule, EntityAction
from app.models.user import User
from app.core.security import hash_password

# 建表
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 检查是否已有数据
if db.query(OntologyEntity).count() > 0:
    print("数据已存在，跳过种子")
    db.close()
    sys.exit(0)

# ── 实体 ──
entities_data = [
    ("customer", "Customer", "客户", 1, "核心客户实体，包含基础信息、消费行为和服务状态"),
    ("order", "Order", "订单", 1, "业务订单实体，记录产品订购和服务开通"),
    ("product", "Product", "产品", 1, "产品目录实体，包含套餐、增值服务等"),
    ("touchpoint", "Touchpoint", "触点", 1, "客户触点记录"),
    ("channel", "Channel", "渠道", 1, "营销和服务渠道"),
    ("agent", "Agent", "坐席", 1, "客服坐席"),
    ("contract", "Contract", "合同", 1, "服务合同"),
    ("campaign", "Campaign", "营销活动", 2, "营销活动实体，管理活动生命周期"),
    ("segment", "CustomerSegment", "客户分群", 2, "基于行为和属性的客户分群"),
    ("strategy", "Strategy", "策略", 2, "营销策略定义"),
    ("ruleset", "RuleSet", "规则集", 2, "业务规则集合"),
    ("fttr_sub", "FTTRSubscription", "FTTR订阅", 3, "FTTR光纤到房间订阅"),
    ("fttr_strat", "FTTRStrategy", "FTTR策略", 3, "FTTR场景智能营销策略"),
]

entity_map = {}
for eid, name, name_cn, tier, desc in entities_data:
    e = OntologyEntity(id=eid, name=name, name_cn=name_cn, tier=tier, status="active", description=desc)
    db.add(e)
    entity_map[eid] = e

db.flush()

# ── 属性（Customer + FTTRSubscription 示例）──
customer_attrs = [
    ("customer_id", "string", "客户唯一标识", True),
    ("name", "string", "客户姓名", True),
    ("phone", "string", "联系电话", True),
    ("arpu", "number", "月均收入", False),
    ("tenure", "number", "在网时长(月)", False),
    ("segment", "ref", "所属分群 → CustomerSegment", False),
    ("ltv_score", "number", "生命周期价值评分", False),
    ("churn_risk", "computed", "流失风险概率 (0-1)", False),
    ("created_at", "date", "创建时间", True),
]
for name, typ, desc, req in customer_attrs:
    db.add(EntityAttribute(entity_id="customer", name=name, type=typ, description=desc, required=req))

fttr_attrs = [
    ("subscription_id", "string", "订阅唯一标识", True),
    ("customer_id", "ref", "关联客户 → Customer", True),
    ("product_id", "ref", "关联产品 → Product", True),
    ("expire_date", "date", "到期日期", True),
    ("days_to_expire", "computed", "距到期天数", False),
    ("monthly_fee", "number", "月费（元）", True),
    ("bandwidth", "string", "带宽规格", True),
    ("auto_renew", "boolean", "是否自动续约", False),
    ("churn_risk", "computed", "流失风险评分 (0-1)", False),
]
for name, typ, desc, req in fttr_attrs:
    db.add(EntityAttribute(entity_id="fttr_sub", name=name, type=typ, description=desc, required=req))

db.flush()

# ── 关系 ──
relations_data = [
    ("customer", "order", "has_order", "has_many", "1:N"),
    ("customer", "fttr_sub", "has_subscription", "has_many", "1:N"),
    ("customer", "segment", "belongs_to_segment", "belongs_to", "N:1"),
    ("customer", "contract", "has_contract", "has_many", "1:N"),
    ("customer", "touchpoint", "has_touchpoint", "has_many", "1:N"),
    ("order", "product", "contains_product", "many_to_many", "N:N"),
    ("campaign", "segment", "targets_segment", "many_to_many", "N:N"),
    ("campaign", "channel", "uses_channel", "many_to_many", "N:N"),
    ("strategy", "ruleset", "applies_rules", "has_many", "1:N"),
    ("strategy", "campaign", "drives_campaign", "has_many", "1:N"),
    ("fttr_sub", "product", "uses_product", "belongs_to", "N:1"),
    ("fttr_strat", "segment", "uses_segment", "many_to_many", "N:N"),
    ("fttr_strat", "product", "promotes_product", "many_to_many", "N:N"),
    ("agent", "touchpoint", "handles", "has_many", "1:N"),
]
for from_id, to_id, name, rel_type, card in relations_data:
    db.add(EntityRelation(from_entity_id=from_id, to_entity_id=to_id, name=name, rel_type=rel_type, cardinality=card))

# ── 规则 ──
rules_data = [
    ("customer", "rule_001", "高价值客户识别", "ltv_score >= 80 AND tenure >= 12", "标记为高价值客户", "active", "high"),
    ("customer", "rule_002", "流失预警", "churn_risk >= 0.7", "触发挽留策略", "active", "high"),
    ("customer", "rule_008", "沉默客户唤醒", "last_active_days > 90", "推送唤醒活动", "active", "medium"),
    ("order", "rule_003", "大额订单审批", "amount >= 5000", "触发人工审批流程", "active", "medium"),
    ("campaign", "rule_004", "预算超限预警", "spend > budget * 0.9", "通知活动负责人", "warning", "high"),
    ("fttr_sub", "rule_005", "到期续约提醒", "days_to_expire <= 30", "发送续约提醒", "active", "high"),
    ("fttr_sub", "rule_006", "欠费预警", "overdue_days > 7", "发送催缴通知", "warning", "medium"),
    ("fttr_sub", "rule_007", "高价值续约", "monthly_fee >= 200 AND churn_risk >= 0.5", "触发专属优惠", "active", "high"),
    ("fttr_strat", "rule_009", "策略效果评估", "actual_conversion < predicted * 0.5", "暂停策略并通知", "active", "low"),
]
for eid, rid, name, cond, action, status, priority in rules_data:
    db.add(BusinessRule(id=rid, entity_id=eid, name=name, condition_expr=cond, action_desc=action, status=status, priority=priority))

# ── 动作 ──
actions_data = [
    ("customer", "发送续约优惠", "campaign"),
    ("customer", "升级FTTR套餐", "upsell"),
    ("fttr_sub", "自动续约", "automation"),
    ("fttr_sub", "到期提醒短信", "notification"),
    ("campaign", "启动活动", "lifecycle"),
    ("segment", "刷新分群", "compute"),
    ("fttr_strat", "执行策略", "automation"),
]
for eid, name, typ in actions_data:
    db.add(EntityAction(entity_id=eid, name=name, type=typ, status="active"))

# ── 管理员 ──
if not db.query(User).filter(User.username == "admin").first():
    db.add(User(username="admin", password_hash=hash_password("admin123"), name="系统管理员", role="admin"))

db.commit()
db.close()

# ── 同步到 Neo4j（可选）──
try:
    from app.services.graph import get_driver, ensure_constraints, upsert_entity_node, create_relation, close_driver
    driver = get_driver()
    ensure_constraints(driver)
    for eid, name, name_cn, tier, desc in entities_data:
        upsert_entity_node(eid, name, name_cn, tier, "active")
    for from_id, to_id, name, rel_type, card in relations_data:
        create_relation(from_id, to_id, name, card)
    close_driver()
    print(f"Neo4j 同步完成: {len(entities_data)} 节点, {len(relations_data)} 关系")
except Exception as e:
    print(f"Neo4j 未连接，跳过图同步: {e}")

print(f"种子数据完成: {len(entities_data)} 实体, {len(relations_data)} 关系, {len(rules_data)} 规则, {len(actions_data)} 动作")
