"""提示词构建工具，负责把项目上下文与元数据组织成模型输入。"""

from __future__ import annotations

import json

from .config import ProjectConfig
from .models import DatabaseMetadata


MAPPING_HEADER = (
    "table_name,subject_class_uri,subject_key_column,column_name,predicate_uri,"
    "object_kind,xsd_datatype,reference_table,reference_column,required,description"
)

DOIM_NAMESPACE = "http://purl.org/doim/1.0#"
BACKEND_CLASSES = [
    "Subscriber",
    "MobileNumber",
    "UsageSnapshot",
    "CommercialSnapshot",
    "ChannelInteraction",
    "RiskFactor",
    "Rule",
    "RiskAlert",
]
BACKEND_PROPERTIES = [
    "ownsNumber",
    "hasUsageSnapshot",
    "hasCommercialSnapshot",
    "hasInteraction",
    "hasRiskFactor",
    "generatedAlert",
    "subscriberId",
    "segmentName",
    "city",
    "planName",
    "tenureMonths",
    "monthlyFee",
    "vipFlag",
    "dataUsageDropPct",
    "voiceUsageDropPct",
    "complaintCount30d",
    "networkIssueCount30d",
    "npsScore",
    "serviceTicketCount30d",
    "contractRemainingDays",
    "overdueDays",
    "competitorContactCount30d",
    "portingCodeRequestCount30d",
    "retentionOfferRejected",
    "paymentRiskLevel",
    "eventId",
    "eventType",
    "channelName",
    "eventDaysAgo",
    "eventSeverity",
    "eventDetail",
    "inferredRiskLevel",
    "recommendedAction",
    "riskLevel",
    "riskScore",
]


def build_messages(config: ProjectConfig, metadata: DatabaseMetadata) -> list[dict[str, str]]:
    """构建提交给模型的 system/user 消息。"""
    metadata_json = json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2)
    business_context_json = json.dumps(config.business_context, ensure_ascii=False, indent=2)
    backend_classes_json = json.dumps(BACKEND_CLASSES, ensure_ascii=False)
    backend_properties_json = json.dumps(BACKEND_PROPERTIES, ensure_ascii=False)

    system = """
You are a senior ontology engineer and data architect.
You convert relational database metadata into backend-compatible ontology design drafts.
Return a single JSON object and nothing else.
The JSON object must contain exactly these keys:
- telecom_ontology_ttl
- telecom_shacl_ttl
- mapping_csv
- rules_yaml
- business_rules_markdown

Rules:
1. All TTL must be valid Turtle syntax.
2. Use full URIs in the mapping_csv, not CURIEs.
3. mapping_csv must use this exact header:
   table_name,subject_class_uri,subject_key_column,column_name,predicate_uri,object_kind,xsd_datatype,reference_table,reference_column,required,description
4. object_kind must be one of: literal, iri_ref
5. xsd_datatype must be an XML Schema datatype URI for literals, or empty for iri_ref.
6. Do not invent business meaning without evidence. If unsure, keep the name conservative.
7. SHACL should focus on required fields, datatype constraints, and simple cardinality constraints.
8. rules_yaml must be valid YAML with top-level keys risk_actions, factor_rules, decision_rules.
9. rule condition field names in rules_yaml must use ontology property local names, not raw database column names.
10. The current backend already provides DOIM core in a separate doim-core.ttl file. Reuse the doim namespace but do not redefine the DOIM core vocabulary in telecom_ontology_ttl.
11. Prefer the current backend telecom class/property local names when the source semantics match.
12. business_rules_markdown should be short and pragmatic.
""".strip()

    user = f"""
Project context:
{business_context_json}

The generated files will be synced into the current backend as:
- backend/ontology/telecom-porting.ttl
- backend/ontology/telecom-shapes.ttl
- backend/rules/porting-risk.yaml

Target namespaces:
- doim namespace: {DOIM_NAMESPACE}
- telecom namespace: {config.ontology.ontology_namespace}
- data namespace: {config.ontology.data_namespace}

Current backend preferred telecom classes:
{backend_classes_json}

Current backend preferred telecom properties:
{backend_properties_json}

Database metadata:
{metadata_json}

Please generate:
1. telecom_ontology_ttl
2. telecom_shacl_ttl
3. mapping_csv
4. rules_yaml
5. business_rules_markdown

The telecom ontology must at least model:
- one class per core table
- object properties for foreign keys
- datatype properties for scalar fields
- conservative domain/range assignments

The SHACL should validate sample instances materialized from mapping_csv.

The rules_yaml must follow this exact backend schema:
- risk_actions: mapping of HIGH/MEDIUM/LOW to action text
- factor_rules: list of items with id, rule_label, factor{{code,label}}, when
- decision_rules: list of items with id, priority, rule_label, when, then{{risk_level}}
- supported condition operators are: >, >=, <, <=, ==, !=, in, not in
- include a LOW default decision rule with an always-true condition such as all: []

If metadata clearly matches the current telecom risk domain, reuse the exact local names from the preferred class/property lists above.
If metadata does not support some current telecom concept, omit that concept rather than inventing a weak synonym.
""".strip()

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def render_prompt_text(messages: list[dict[str, str]]) -> str:
    """把消息列表渲染为便于人工检查的纯文本提示词。"""
    chunks: list[str] = []
    for message in messages:
        chunks.append(f"[{message['role'].upper()}]\n{message['content']}")
    return "\n\n".join(chunks) + "\n"
