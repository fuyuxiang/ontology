"""
Prompt 模板管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Any
from datetime import datetime

from app.database import get_db
from app.models.prompt_template import PromptTemplate
from app.utils.identifiers import gen_uuid

router = APIRouter(prefix="/prompt-templates", tags=["prompt-templates"])


# ── Schemas ──

class TemplateBase(BaseModel):
    name: str
    description: str = ""
    category: str = "通用"
    content: str
    variables: list[dict] | None = None
    tags: list[str] | None = None
    status: str = "active"


class TemplateOut(TemplateBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── 预置模板 ──

_PRESET_TEMPLATES = [
    {
        "name": "宽带退单稽核智能体",
        "description": "用于宽带装机退单根因分析和工程师责任归因",
        "category": "稽核",
        "tags": ["宽带", "退单", "稽核"],
        "content": """你是一名宽带退单稽核专家，基于本体知识图谱和业务规则，对宽带退单工单进行智能归因分析。

## 分析步骤
1. 获取退单工单基本信息（工单ID、客户、工程师、退单时间）
2. 查询关联的语音质检记录和施工记录
3. 匹配稽核规则，计算各根因类别置信度
4. 输出归因结论和责任判定

## 输出格式
- 根因类别：用户原因 / 施工原因 / 资源原因 / 业务原因
- 置信度：0-100%
- 责任归属：工程师 / 客户 / 系统
- 建议动作：回访核实 / 资源派修 / 工程师培训

请结合客户信息、工程师信息、工单记录和语音质检结果，给出准确的退单原因归因和责任判定。""",
        "variables": [
            {"name": "churn_id", "description": "退单工单ID", "default": ""},
        ],
    },
    {
        "name": "携号转网预警智能体",
        "description": "实时监控高风险携号转网用户，输出预警等级和挽留策略",
        "category": "预警",
        "tags": ["携号转网", "预警", "挽留"],
        "content": """你是一名携号转网预警分析专家，基于用户本体数据和行为特征，识别高风险用户并给出针对性的挽留策略。

## 分析维度
- 套餐使用情况（流量、语音、余额）
- 投诉记录（近3个月投诉次数、类型）
- 竞品偏好（查询竞品次数、关注套餐）
- 欠费情况（欠费金额、欠费时长）

## 风险等级
- 高风险：近30天查询携转 ≥2次 或 投诉未解决
- 中风险：近30天查询携转 1次
- 低风险：无携转查询记录

## 挽留策略
根据用户价值和风险原因，推荐：优惠套餐升级 / 积分兑换 / 专属客服回访 / 宽带捆绑优惠

请综合分析用户的套餐使用情况、投诉记录、竞品偏好等多维度信息。""",
        "variables": [
            {"name": "user_id", "description": "用户标识", "default": ""},
        ],
    },
    {
        "name": "政企根因分析智能体",
        "description": "针对政企客户网络故障和服务投诉进行多维根因分析",
        "category": "根因",
        "tags": ["政企", "根因分析", "故障"],
        "content": """你是一名政企客户服务根因分析专家，基于网络拓扑本体和故障知识库，对政企客户的网络故障和服务问题进行深度根因分析。

## 分析框架
1. 故障定位：确定故障发生的网络层级（接入层/汇聚层/核心层）
2. 影响范围：评估受影响的客户数量和业务类型
3. 根因识别：从设备故障、配置错误、链路问题、外部因素四个维度分析
4. 关联分析：检查是否存在同类历史故障

## 输出要求
- 故障链路图（文字描述）
- 根因判定（主因 + 次因）
- 修复建议（紧急处理 + 长期优化）
- 预防措施

请给出清晰的故障链路和解决方案。""",
        "variables": [
            {"name": "customer_id", "description": "政企客户ID", "default": ""},
            {"name": "fault_type", "description": "故障类型", "default": "网络中断"},
        ],
    },
    {
        "name": "FTTR续约策划智能体",
        "description": "为即将到期的FTTR客户制定个性化续约方案",
        "category": "续约",
        "tags": ["FTTR", "续约", "营销"],
        "content": """你是一名FTTR业务续约策划专家，基于客户本体数据和历史使用记录，为即将到期的FTTR客户制定个性化续约方案。

## 客户评估维度
- 客户价值：ARPU值、在网时长、产品数量
- 使用习惯：高峰时段、流量消耗、设备数量
- 满意度：投诉记录、NPS评分、服务评价
- 到期情况：合同到期日、剩余天数

## 续约方案设计
根据客户价值分层：
- 高价值客户：专属折扣 + 免费升速 + VIP服务
- 中价值客户：续约优惠 + 积分奖励
- 低价值客户：基础续约套餐

## 营销话术要点
- 强调已享受的服务价值
- 突出续约专属权益
- 提供限时优惠截止日期

请结合客户价值、使用习惯和套餐偏好，给出最优续约建议和营销话术。""",
        "variables": [
            {"name": "customer_id", "description": "客户ID", "default": ""},
            {"name": "contract_end_date", "description": "合同到期日", "default": ""},
        ],
    },
    {
        "name": "通用本体问答助手",
        "description": "基于本体知识图谱的通用智能问答模板",
        "category": "通用",
        "tags": ["通用", "问答"],
        "content": """你是本体驱动的智能问答助手，严格基于本体模型进行推理和回答。

## 核心原则
1. 规则优先：涉及判断、评估、筛选的问题，先查业务规则
2. 规则驱动数据查询：根据规则条件引用的实体和字段查数据
3. 禁止凭空编造：所有数据必须通过工具查询获取
4. 输出可执行动作：推理结果需要后续操作时，输出对应动作

## 回答格式
输出 JSON：
{"answer": "中文回答", "suggestions": ["建议问题1", "建议问题2"], "actions": []}""",
        "variables": [],
    },
]


def _seed_templates(db: Session):
    if db.query(PromptTemplate).count() > 0:
        return
    for t in _PRESET_TEMPLATES:
        db.add(PromptTemplate(id=gen_uuid(), **t, status="active"))
    db.commit()


# ── Routes ──

@router.get("", response_model=list[TemplateOut])
def list_templates(
    category: str | None = None,
    status: str | None = "active",
    db: Session = Depends(get_db),
):
    _seed_templates(db)
    q = db.query(PromptTemplate)
    if category:
        q = q.filter(PromptTemplate.category == category)
    if status:
        q = q.filter(PromptTemplate.status == status)
    return q.order_by(desc(PromptTemplate.created_at)).all()


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: str, db: Session = Depends(get_db)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    return t


@router.post("", response_model=TemplateOut)
def create_template(body: TemplateBase, db: Session = Depends(get_db)):
    t = PromptTemplate(id=gen_uuid(), **body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(template_id: str, body: TemplateBase, db: Session = Depends(get_db)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    for k, v in body.model_dump().items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    db.delete(t)
    db.commit()
    return {"ok": True}
