"""
OSDK 代码生成引擎 — 根据本体 Schema 生成 TypeScript/Python SDK
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import OntologyEntity, EntityRelation


ATTR_TYPE_MAP_TS = {
    "string": "string",
    "number": "number",
    "boolean": "boolean",
    "date": "string",
    "json": "Record<string, any>",
    "ref": "string",
    "computed": "string",
    "enum": "string",
}

ATTR_TYPE_MAP_PY = {
    "string": "str",
    "number": "float",
    "boolean": "bool",
    "date": "str",
    "json": "dict",
    "ref": "str",
    "computed": "str",
    "enum": "str",
}


def generate_sdk(db: Session, language: str, entity_ids: list[str] | None = None) -> dict:
    query = db.query(OntologyEntity).filter(OntologyEntity.status == "published")
    if entity_ids:
        query = query.filter(OntologyEntity.id.in_(entity_ids))
    entities = query.all()

    relations = db.query(EntityRelation).all()
    rel_map: dict[str, list] = {}
    for r in relations:
        rel_map.setdefault(r.from_entity_id, []).append(r)

    if language == "python":
        return _generate_python(entities, rel_map)
    return _generate_typescript(entities, rel_map)


def _generate_typescript(entities: list, rel_map: dict) -> dict:
    files = []

    # index.ts
    imports = []
    exports = []
    for entity in entities:
        imports.append(f"export {{ {entity.name}, type {entity.name}Props }} from './{entity.name}';")
        exports.append(entity.name)

    index_content = "// Auto-generated Ontology SDK\n"
    index_content += f"// Entities: {len(entities)}\n\n"
    index_content += "\n".join(imports)
    index_content += "\n\nexport { OntologyClient } from './client';\n"
    files.append({"name": "index.ts", "content": index_content})

    # client.ts
    client_content = """import axios, { AxiosInstance } from 'axios';

export class OntologyClient {
  private http: AxiosInstance;

  constructor(baseURL: string, apiKey?: string) {
    this.http = axios.create({
      baseURL,
      headers: apiKey ? { 'X-API-Key': apiKey } : {},
    });
  }

  async query<T>(entityName: string, params?: Record<string, any>): Promise<T[]> {
    const res = await this.http.get(`/ontology-api/objects/${entityName}`, { params });
    return res.data;
  }

  async getById<T>(entityName: string, id: string): Promise<T> {
    const res = await this.http.get(`/ontology-api/objects/${entityName}/${id}`);
    return res.data;
  }

  async getRelations(entityName: string, id: string, depth = 1): Promise<any[]> {
    const res = await this.http.get(`/ontology-api/objects/${entityName}/${id}/relations`, { params: { depth } });
    return res.data;
  }
}
"""
    files.append({"name": "client.ts", "content": client_content})

    # Entity files
    for entity in entities:
        attrs = entity.attributes or []
        props_lines = []
        for attr in attrs:
            ts_type = ATTR_TYPE_MAP_TS.get(attr.get("type", "string"), "any")
            required = "?" if not attr.get("required") else ""
            props_lines.append(f"  {attr['name']}{required}: {ts_type};")

        rels = rel_map.get(entity.id, [])
        rel_methods = []
        for r in rels:
            rel_methods.append(f"  async {r.name}(): Promise<any[]> {{ return this.client.getRelations('{entity.name}', this.id); }}")

        content = f"""import {{ OntologyClient }} from './client';

export interface {entity.name}Props {{
{chr(10).join(props_lines) if props_lines else '  [key: string]: any;'}
}}

export class {entity.name} {{
  readonly id: string;
  readonly props: {entity.name}Props;
  private client: OntologyClient;

  constructor(id: string, props: {entity.name}Props, client: OntologyClient) {{
    this.id = id;
    this.props = props;
    this.client = client;
  }}

  static async list(client: OntologyClient, params?: Record<string, any>): Promise<{entity.name}[]> {{
    const data = await client.query<any>('{entity.name}', params);
    return data.map((d: any) => new {entity.name}(d.id, d, client));
  }}

  static async get(client: OntologyClient, id: string): Promise<{entity.name}> {{
    const data = await client.getById<any>('{entity.name}', id);
    return new {entity.name}(data.id, data, client);
  }}

{chr(10).join(rel_methods) if rel_methods else ''}}}
"""
        files.append({"name": f"{entity.name}.ts", "content": content})

    usage = f"""import {{ OntologyClient, {entities[0].name if entities else 'Entity'} }} from './ontology-sdk';

const client = new OntologyClient('http://localhost:8001/api/v1', 'your-api-key');

// 查询实体列表
const items = await {entities[0].name if entities else 'Entity'}.list(client, {{ limit: 10 }});

// 获取单个实体
const item = await {entities[0].name if entities else 'Entity'}.get(client, 'entity-id');
console.log(item.props);
"""

    return {"files": files, "usage": usage}


def _generate_python(entities: list, rel_map: dict) -> dict:
    files = []

    # __init__.py
    init_lines = ["# Auto-generated Ontology SDK"]
    for entity in entities:
        init_lines.append(f"from .{entity.name.lower()} import {entity.name}")
    init_lines.append("from .client import OntologyClient")
    files.append({"name": "__init__.py", "content": "\n".join(init_lines) + "\n"})

    # client.py
    client_content = """import httpx
from typing import Any


class OntologyClient:
    def __init__(self, base_url: str, api_key: str | None = None):
        headers = {"X-API-Key": api_key} if api_key else {}
        self.http = httpx.Client(base_url=base_url, headers=headers)

    def query(self, entity_name: str, **params) -> list[dict]:
        res = self.http.get(f"/ontology-api/objects/{entity_name}", params=params)
        res.raise_for_status()
        return res.json()

    def get_by_id(self, entity_name: str, id: str) -> dict:
        res = self.http.get(f"/ontology-api/objects/{entity_name}/{id}")
        res.raise_for_status()
        return res.json()

    def get_relations(self, entity_name: str, id: str, depth: int = 1) -> list[dict]:
        res = self.http.get(f"/ontology-api/objects/{entity_name}/{id}/relations", params={"depth": depth})
        res.raise_for_status()
        return res.json()
"""
    files.append({"name": "client.py", "content": client_content})

    # Entity files
    for entity in entities:
        attrs = entity.attributes or []
        field_lines = []
        for attr in attrs:
            py_type = ATTR_TYPE_MAP_PY.get(attr.get("type", "string"), "Any")
            default = " = None" if not attr.get("required") else ""
            field_lines.append(f"    {attr['name']}: {py_type}{default}")

        content = f"""from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .client import OntologyClient


@dataclass
class {entity.name}:
    id: str
{chr(10).join(field_lines) if field_lines else '    pass'}

    @classmethod
    def list(cls, client: OntologyClient, **params) -> list[{entity.name}]:
        data = client.query("{entity.name}", **params)
        return [cls(id=d["id"], **{{k: d.get(k) for k in cls.__dataclass_fields__ if k != "id"}}) for d in data]

    @classmethod
    def get(cls, client: OntologyClient, id: str) -> {entity.name}:
        data = client.get_by_id("{entity.name}", id)
        return cls(id=data["id"], **{{k: data.get(k) for k in cls.__dataclass_fields__ if k != "id"}})

    def relations(self, client: OntologyClient, depth: int = 1) -> list[dict]:
        return client.get_relations("{entity.name}", self.id, depth)
"""
        files.append({"name": f"{entity.name.lower()}.py", "content": content})

    usage = f"""from ontology_sdk import OntologyClient, {entities[0].name if entities else 'Entity'}

client = OntologyClient("http://localhost:8001/api/v1", api_key="your-api-key")

# 查询实体列表
items = {entities[0].name if entities else 'Entity'}.list(client, limit=10)

# 获取单个实体
item = {entities[0].name if entities else 'Entity'}.get(client, "entity-id")
print(item)
"""

    return {"files": files, "usage": usage}
