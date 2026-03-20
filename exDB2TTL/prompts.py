from __future__ import annotations

import json

from .config import ProjectConfig
from .models import DatabaseMetadata


MAPPING_HEADER = (
    "table_name,subject_class_uri,subject_key_column,column_name,predicate_uri,"
    "object_kind,xsd_datatype,reference_table,reference_column,required,description"
)


def build_messages(config: ProjectConfig, metadata: DatabaseMetadata) -> list[dict[str, str]]:
    metadata_json = json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2)
    business_context_json = json.dumps(config.business_context, ensure_ascii=False, indent=2)

    system = """
You are a senior ontology engineer and data architect.
You convert relational database metadata into ontology design drafts.
Return a single JSON object and nothing else.
The JSON object must contain exactly these keys:
- ontology_ttl
- shacl_ttl
- mapping_csv
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
8. business_rules_markdown should be short and pragmatic.
""".strip()

    user = f"""
Project context:
{business_context_json}

Target namespaces:
- ontology namespace: {config.ontology.ontology_namespace}
- data namespace: {config.ontology.data_namespace}

Database metadata:
{metadata_json}

Please generate:
1. ontology_ttl
2. shacl_ttl
3. mapping_csv
4. business_rules_markdown

The ontology must at least model:
- one class per core table
- object properties for foreign keys
- datatype properties for scalar fields
- conservative domain/range assignments

The SHACL should validate sample instances materialized from mapping_csv.
""".strip()

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def render_prompt_text(messages: list[dict[str, str]]) -> str:
    chunks: list[str] = []
    for message in messages:
        chunks.append(f"[{message['role'].upper()}]\n{message['content']}")
    return "\n\n".join(chunks) + "\n"
