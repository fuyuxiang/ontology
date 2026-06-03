"""Unified ontology extraction constraints: prompt building, validation, retry."""

import json
import logging
import re

from pydantic import ValidationError

from app.schemas.ontology_output import OntologyOutput

logger = logging.getLogger(__name__)

NAMING_CONSTRAINTS = """
## 命名规范（必须严格遵守）
1. 实体名(name)：PascalCase，2-4个英文单词，缩略词大写（如BSS、CRM）
2. 属性名(name)：snake_case，不超过40字符
3. 关系名(name)：camelCase，动词短语形式（如subscribesTo、belongsTo）
4. 中文名(name_cn/display_name)：≤10个汉字，不含标点
"""

TIER_DECISION_TREE = """
## 层级判定规则（tier字段）
- T1 核心对象（tier=1）：跨3个以上业务场景复用 → 客户、用户、账户、产品、套餐、资费、订单、工单
- T2 领域对象（tier=2）：在单个业务域内被多场景引用 → 设备、网元、资源、合约、账单、渠道
- T3 场景对象（tier=3）：仅在当前场景内使用 → 分析结果、临时标签、中间状态
判定步骤：
1. 该对象是否在联通T1列表中？→ tier=1
2. 该对象是否被多个场景引用？→ tier=2
3. 其余 → tier=3
"""

TELECOM_KNOWLEDGE = """
## 联通领域知识
- "客户"是签约主体（持有身份证/营业执照），"用户"是使用主体（持有手机号/宽带账号）—— 二者必须区分
- "套餐"是面向客户的打包方案，"产品"是可组合的原子能力 —— 套餐包含产品
- 常见关系模式参考：客户→订购→产品、产品→包含→资费组件、客户→发起→工单、设备→产生→告警
- BSS（业务支撑）管CRM/计费/账务，OSS（运营支撑）管网络/告警/性能
"""

OUTPUT_FORMAT = """
## 输出格式（严格JSON，不要包含其他文字）
{{"entities": [{{"name": "PascalCase英文名", "name_cn": "中文名", "tier": 1, "description": "业务描述", "attributes": [{{"name": "snake_case", "display_name": "中文名", "type": "string|number|boolean|date|json|ref|computed|enum", "required": true, "description": "说明"}}]}}], "relations": [{{"from_entity": "源实体name", "to_entity": "目标实体name", "name": "camelCase关系名", "rel_type": "has_one|has_many|belongs_to|many_to_many", "cardinality": "1:1|1:N|N:1|N:N"}}]}}
"""


def build_constraint_prompt(existing_entities: list[str] | None = None) -> str:
    parts = [NAMING_CONSTRAINTS, TIER_DECISION_TREE, TELECOM_KNOWLEDGE, OUTPUT_FORMAT]
    if existing_entities:
        entity_list = "、".join(existing_entities)
        parts.append(f"\n## 已有实体（避免重复创建，优先建立关联）\n{entity_list}\n")
    return "\n".join(parts)
