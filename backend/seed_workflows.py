"""预置3个工作流场景"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, Base, engine
from app.models.workflow import Workflow, gen_uuid
from datetime import datetime

# 确保表存在
Base.metadata.create_all(bind=engine)

PRESETS = [
    {
        "name": "续约智能策划",
        "description": "基于本体查询识别高价值续约客户，经规则引擎筛选后由大模型生成个性化策划方案，最终触达通知",
        "namespace": "s1",
        "group_name": "营销场景",
        "nodes_json": [
            {"id": "n1", "type": "ontology-query", "position": {"x": 60, "y": 120}, "data": {"label": "查询续约客户", "ontology_type": "InstallOrder", "execState": "pending"}},
            {"id": "n2", "type": "rule-engine",    "position": {"x": 280, "y": 120}, "data": {"label": "高价值筛选规则", "execState": "pending"}},
            {"id": "n3", "type": "llm-inference",  "position": {"x": 500, "y": 120}, "data": {"label": "生成策划方案", "prompt": "根据客户信息{customer}生成续约策划方案", "execState": "pending"}},
            {"id": "n4", "type": "notification",   "position": {"x": 720, "y": 120}, "data": {"label": "触达通知", "notify_type": "sms", "execState": "pending"}},
        ],
        "edges_json": [
            {"id": "e1-2", "source": "n1", "target": "n2", "type": "smoothstep"},
            {"id": "e2-3", "source": "n2", "target": "n3", "type": "smoothstep"},
            {"id": "e3-4", "source": "n3", "target": "n4", "type": "smoothstep"},
        ],
    },
    {
        "name": "宽带退单归因",
        "description": "从数据源拉取退单工单，规则引擎初步归因，大模型深度分析原因，写回本体并推送人工审批",
        "namespace": "broadband",
        "group_name": "稽核场景",
        "nodes_json": [
            {"id": "n1", "type": "datasource",     "position": {"x": 60,  "y": 120}, "data": {"label": "拉取退单工单", "sql": "SELECT * FROM churn_orders WHERE status='pending' LIMIT 100", "execState": "pending"}},
            {"id": "n2", "type": "rule-engine",    "position": {"x": 280, "y": 120}, "data": {"label": "初步归因规则", "execState": "pending"}},
            {"id": "n3", "type": "llm-inference",  "position": {"x": 500, "y": 120}, "data": {"label": "深度原因分析", "prompt": "分析以下退单工单的根本原因：{order_data}", "execState": "pending"}},
            {"id": "n4", "type": "write-back",     "position": {"x": 500, "y": 280}, "data": {"label": "写回归因结果", "execState": "pending"}},
            {"id": "n5", "type": "human-approval", "position": {"x": 720, "y": 200}, "data": {"label": "运营主管审批", "approver_role": "运营主管", "execState": "pending"}},
        ],
        "edges_json": [
            {"id": "e1-2", "source": "n1", "target": "n2", "type": "smoothstep"},
            {"id": "e2-3", "source": "n2", "target": "n3", "type": "smoothstep"},
            {"id": "e3-4", "source": "n3", "target": "n4", "type": "smoothstep"},
            {"id": "e3-5", "source": "n3", "target": "n5", "type": "smoothstep"},
        ],
    },
    {
        "name": "政企智能问数",
        "description": "查询政企客户本体实例，大模型将自然语言问题转换为结构化查询并生成分析报告",
        "namespace": "enterprise",
        "group_name": "政企场景",
        "nodes_json": [
            {"id": "n1", "type": "ontology-query", "position": {"x": 60,  "y": 120}, "data": {"label": "查询政企客户", "ontology_type": "EnterpriseCustomer", "execState": "pending"}},
            {"id": "n2", "type": "llm-inference",  "position": {"x": 280, "y": 120}, "data": {"label": "NL转结构化查询", "prompt": "将问题「{question}」转换为针对政企客户数据的结构化查询", "execState": "pending"}},
            {"id": "n3", "type": "datasource",     "position": {"x": 500, "y": 120}, "data": {"label": "执行数据查询", "sql": "SELECT * FROM enterprise_stats", "execState": "pending"}},
            {"id": "n4", "type": "llm-inference",  "position": {"x": 720, "y": 120}, "data": {"label": "生成分析报告", "prompt": "根据查询结果{data}生成业务分析报告", "execState": "pending"}},
        ],
        "edges_json": [
            {"id": "e1-2", "source": "n1", "target": "n2", "type": "smoothstep"},
            {"id": "e2-3", "source": "n2", "target": "n3", "type": "smoothstep"},
            {"id": "e3-4", "source": "n3", "target": "n4", "type": "smoothstep"},
        ],
    },
]

def seed():
    db = SessionLocal()
    try:
        for p in PRESETS:
            exists = db.query(Workflow).filter(Workflow.name == p["name"]).first()
            if exists:
                print(f"  skip (already exists): {p['name']}")
                continue
            w = Workflow(
                id=gen_uuid(),
                name=p["name"],
                description=p["description"],
                namespace=p["namespace"],
                group_name=p["group_name"],
                nodes_json=p["nodes_json"],
                edges_json=p["edges_json"],
                trigger_config={},
                status="draft",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(w)
            print(f"  created: {p['name']}")
        db.commit()
        print("Done.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
