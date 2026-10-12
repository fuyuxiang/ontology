"""Generate importable clients from the actual published ORM schema."""
from __future__ import annotations
import json
import keyword
import re
from app.models.version import OntologyVersion, OntologyVersionEntity

ATTR_TYPE_MAP_TS = {"string": "string", "number": "number", "integer": "number", "boolean": "boolean", "date": "string", "json": "Record<string, unknown>", "ref": "string"}
ATTR_TYPE_MAP_PY = {"string": "str", "number": "float", "integer": "int", "boolean": "bool", "date": "str", "json": "dict", "ref": "str"}


def _symbol(name):
    result = re.sub(r"\W", "_", name or "Entity")
    if not result.isidentifier() or keyword.iskeyword(result) or result in {"class", "function", "default", "interface", "export", "import", "new", "constructor"}:
        result = "Entity_" + result
    return result


def _attr(attr, key, default=None):
    return attr.get(key, default) if isinstance(attr, dict) else getattr(attr, key, default)


def _identity_property(entity):
    snapshot = getattr(entity, "binding_snapshot", None) or {}
    column = snapshot.get("id_column")
    if not column:
        # Legacy schema-only inputs have no binding metadata.
        return "id"
    attribute_ids = {mapping.get("attribute_id") for mapping in snapshot.get("field_mappings") or []
                     if mapping.get("source_column") == column}
    names = [_attr(attr, "name") for attr in entity.attributes
             if _attr(attr, "source_attribute_id") in attribute_ids]
    if len(names) != 1:
        raise ValueError("发布对象必须映射唯一实例 ID 属性，才能生成 SDK")
    return names[0]


def generate_sdk(db, language, entity_ids=None):
    if language not in ("typescript", "python"):
        raise ValueError("language 必须为 typescript 或 python")
    query = db.query(OntologyVersionEntity).join(OntologyVersion).filter(OntologyVersion.status == "published", OntologyVersion.is_active.is_(True))
    if entity_ids:
        query = query.filter(OntologyVersionEntity.source_entity_id.in_(entity_ids))
    entities = query.all()
    names = {}
    # Filenames must also be unique on case-insensitive filesystems, and
    # generated objects must not replace client/index or TS Props symbols.
    used = {"client", "index", "__init__", "ontologyclient"}
    for entity in entities:
        base = _symbol(entity.name)
        symbol = base
        suffix = entity.source_entity_id.replace("-", "")[:8]
        while symbol.casefold() in used or (symbol + "Props").casefold() in used:
            symbol += "_" + suffix
        names[entity.id] = symbol
        used.update({symbol.casefold(), (symbol + "Props").casefold()})
    return _generate_python(entities, {}, names) if language == "python" else _generate_typescript(entities, {}, names)


def _generate_typescript(entities, rel_map, names=None):
    names = names or {e.id: _symbol(e.name) for e in entities}
    files = [{"name": "client.ts", "content": '''export interface RelationPagination {
  limit?: number;
  offset?: number;
  relation_id?: string;
  max_nodes?: number;
}
export class OntologyClient {
  constructor(private baseURL: string, private token?: string, private apiKey?: string) {}
  private async request<T>(path: string, params: Record<string, unknown> = {}): Promise<T> {
    const url = new URL(this.baseURL.replace(/\\/$/, '') + '/' + path);
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
    }
    const headers: Record<string, string> = {};
    if (this.token) headers.Authorization = 'Bearer ' + this.token;
    if (this.apiKey) headers['X-API-Key'] = this.apiKey;
    const response = await fetch(url, { headers });
    if (!response.ok) throw new Error(`Ontology API ${response.status}: ${await response.text()}`);
    return response.json() as Promise<T>;
  }
  query<T>(entity: string, params: Record<string, unknown> = {}): Promise<T[]> {
    return this.request<T[]>('ontology-api/objects/' + encodeURIComponent(entity), params);
  }
  getById<T>(entity: string, id: string, params: Record<string, unknown> = {}): Promise<T> {
    return this.request<T>('ontology-api/objects/' + encodeURIComponent(entity) + '/' + encodeURIComponent(id), params);
  }
  getRelations(entity: string, id: string, depth = 1, relType?: string, versionId?: string, pagination: RelationPagination = {}): Promise<Record<string, unknown>[]> {
    return this.request('ontology-api/objects/' + encodeURIComponent(entity) + '/' + encodeURIComponent(id) + '/relations', {...pagination, depth, rel_type: relType, version_id: versionId});
  }
}
'''}]
    exports = []
    for entity in entities:
        symbol = names[entity.id]
        endpoint = getattr(entity, "source_entity_id", entity.id)
        version = getattr(entity, "version_id", None)
        identity_property = _identity_property(entity)
        props = [f"  {json.dumps(_attr(a, 'name'))}{'' if _attr(a, 'required') or _attr(a, 'name') == identity_property else '?'}: {ATTR_TYPE_MAP_TS.get(_attr(a, 'type'), 'unknown')};" for a in entity.attributes]
        if not any(_attr(a, "name") == "id" for a in entity.attributes):
            identity_type = next((ATTR_TYPE_MAP_TS.get(_attr(a, "type"), "unknown") for a in entity.attributes
                                  if _attr(a, "name") == identity_property), "string")
            props.insert(0, f"  id: {identity_type};")
        content = f'''import {{ OntologyClient, type RelationPagination }} from './client';
export interface {symbol}Props {{
{chr(10).join(props)}
}}
export class {symbol} {{
  constructor(readonly id: string, readonly props: {symbol}Props, private client: OntologyClient) {{}}
  static async list(client: OntologyClient, params: Record<string, unknown> = {{}}): Promise<{symbol}[]> {{
    const data = await client.query<{symbol}Props>({json.dumps(endpoint)}, {{...params, version_id: {json.dumps(version)}}});
    return data.map(d => new {symbol}(String(d[{json.dumps(identity_property)}]), d, client));
  }}
  static async get(client: OntologyClient, id: string): Promise<{symbol}> {{
    const data = await client.getById<{symbol}Props>({json.dumps(endpoint)}, id, {{version_id: {json.dumps(version)}}});
    return new {symbol}(String(data[{json.dumps(identity_property)}]), data, client);
  }}
  relations(depth = 1, relType?: string, pagination: RelationPagination = {{}}): Promise<Record<string, unknown>[]> {{
    return this.client.getRelations({json.dumps(endpoint)}, this.id, depth, relType, {json.dumps(version)}, pagination);
  }}
}}
'''
        files.append({"name": symbol + ".ts", "content": content})
        exports.append(f"export {{ {symbol}, type {symbol}Props }} from './{symbol}';")
    files.append({"name": "index.ts", "content": "export { OntologyClient, type RelationPagination } from './client';\n" + "\n".join(exports) + "\n"})
    example = names[entities[0].id] if entities else None
    usage = "import { OntologyClient" + (", " + example if example else "") + " } from './ontology-sdk';\nconst client = new OntologyClient('http://localhost:8001/api/v1', 'YOUR_JWT');\n"
    if example:
        usage += f"const instances = await {example}.list(client, {{limit: 10, filter: {{}}}});\n"
    return {"files": files, "usage": usage}


def _generate_python(entities, rel_map, names=None):
    names = names or {e.id: _symbol(e.name) for e in entities}
    files = [{"name": "client.py", "content": '''import json
from urllib.parse import quote
import httpx

class OntologyClient:
    def __init__(self, base_url: str, token: str | None = None, api_key: str | None = None):
        headers = {}
        if token: headers['Authorization'] = 'Bearer ' + token
        if api_key: headers['X-API-Key'] = api_key
        self.http = httpx.Client(base_url=base_url.rstrip('/') + '/', headers=headers)
    def _get(self, path, params=None):
        encoded = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in (params or {}).items() if v is not None}
        response = self.http.get(path, params=encoded)
        response.raise_for_status()
        return response.json()
    def query(self, entity_name, **params):
        return self._get('ontology-api/objects/' + quote(entity_name, safe=''), params)
    def get_by_id(self, entity_name, id, **params):
        return self._get('ontology-api/objects/' + quote(entity_name, safe='') + '/' + quote(str(id), safe=''), params)
    def get_relations(self, entity_name, id, depth=1, rel_type=None, version_id=None, *, limit=None, offset=0, relation_id=None, max_nodes=None):
        return self._get('ontology-api/objects/' + quote(entity_name, safe='') + '/' + quote(str(id), safe='') + '/relations', {'depth': depth, 'rel_type': rel_type, 'version_id': version_id, 'limit': limit, 'offset': offset, 'relation_id': relation_id, 'max_nodes': max_nodes})
    def close(self):
        self.http.close()
'''}]
    exports = ["from .client import OntologyClient"]
    for entity in entities:
        symbol = names[entity.id]
        endpoint = getattr(entity, "source_entity_id", entity.id)
        version = getattr(entity, "version_id", None)
        identity_property = _identity_property(entity)
        fields, mapping, used = [], {}, {"id"}
        for attr in entity.attributes:
            name = _attr(attr, "name")
            if name == "id" and identity_property == "id":
                continue
            field = _symbol(name)
            while field in used or field in {"list", "get", "relations", "_field_map"}:
                field += "_"
            used.add(field)
            mapping[field] = name
            typ = ATTR_TYPE_MAP_PY.get(_attr(attr, "type"), "Any")
            fields.append(f"    {field}: {typ}{'' if _attr(attr, 'required') else ' | None = None'}")
        content = f'''from __future__ import annotations
from dataclasses import dataclass
from typing import Any, ClassVar
from .client import OntologyClient

@dataclass(kw_only=True)
class {symbol}:
    id: str
{chr(10).join(fields)}
    _field_map: ClassVar[dict] = {mapping!r}
    @classmethod
    def _from_data(cls, data):
        return cls(id=str(data[{identity_property!r}]), **{{field: data.get(name) for field, name in cls._field_map.items()}})
    @classmethod
    def list(cls, client: OntologyClient, **params):
        params['version_id'] = {version!r}
        return [cls._from_data(row) for row in client.query({endpoint!r}, **params)]
    @classmethod
    def get(cls, client: OntologyClient, id: str):
        return cls._from_data(client.get_by_id({endpoint!r}, id, version_id={version!r}))
    def relations(self, client: OntologyClient, depth=1, rel_type=None, **pagination):
        return client.get_relations({endpoint!r}, self.id, depth, rel_type, {version!r}, **pagination)
'''
        module = symbol.lower()
        exports.append(f"from .{module} import {symbol}")
        files.append({"name": module + ".py", "content": content})
    files.append({"name": "__init__.py", "content": "\n".join(exports) + "\n"})
    example = names[entities[0].id] if entities else None
    usage = "from ontology_sdk import OntologyClient" + (", " + example if example else "") + "\nclient = OntologyClient('http://localhost:8001/api/v1', token='YOUR_JWT')\n"
    if example:
        usage += f"instances = {example}.list(client, limit=10, filter={{}})\n"
    return {"files": files, "usage": usage}
