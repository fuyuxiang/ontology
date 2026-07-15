"""
Agent 工具路由 — 工具分发与执行
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import EntityRelation, OntologyEntity
from app.services.action_executors import run_executor_sync
from app.services.data_plane.entity_data_service import EntityDataService

logger = logging.getLogger(__name__)


class ToolRouter:
    def __init__(self, db: Session, runtime_executor=None):
        self.db = db
        self.runtime_executor = runtime_executor

    def execute(self, tool_name: str, args: dict) -> tuple[Any, str, int]:
        handlers = {
            "describe_ontology_model": self._tool_describe_ontology_model,
            "list_datasources": self._tool_list_datasources,
            "get_table_schema": self._tool_get_table_schema,
            "query_datasource": self._tool_query_datasource,
            "get_entity_detail": self._tool_get_entity_detail,
            "query_entity_data": self._tool_query_entity_data,
            "execute_action": self._tool_execute_action,
            # 本体构建器（chat 模式）三件套
            "list_business_datasources": self._tool_list_business_datasources,
            "list_business_documents": self._tool_list_business_documents,
            "analyze_assets_for_ontology": self._tool_analyze_assets_for_ontology,
            # Tier 1: 数据查询（重构）
            "ontology_query_instances": self._tool_query_instances,
            "ontology_get_attr_mapping": self._tool_get_attr_mapping,
            "ontology_complex_sql": self._tool_complex_sql,
            # Tier 2: 逻辑/动作调用
            "ontology_list_capabilities": self._tool_list_capabilities,
            "ontology_run_logic": self._tool_run_logic,
            "ontology_run_action": self._tool_run_action,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"未知工具: {tool_name}"}, f"未知工具 {tool_name}", 0
        try:
            return handler(args)
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            return {"error": str(e)}, f"执行失败: {e}", 0

    def _tool_describe_ontology_model(self, args: dict) -> tuple[Any, str, int]:
        published = self.db.query(OntologyEntity).filter(OntologyEntity.status == "published").all()
        entities = published if published else self.db.query(OntologyEntity).all()
        entity_ids = {e.id for e in entities}
        relations = [
            r for r in self.db.query(EntityRelation).all()
            if r.from_entity_id in entity_ids and r.to_entity_id in entity_ids
        ]

        tier_names = {1: "核心", 2: "领域", 3: "场景"}
        entity_list = []
        for e in entities:
            attrs = [{"name": a.name, "type": a.type, "description": a.description} for a in e.attributes]
            entity_list.append({
                "name": e.name, "name_cn": e.name_cn,
                "tier": e.tier, "tierLabel": tier_names.get(e.tier, ""),
                "attrCount": len(attrs), "attributes": attrs[:10],
            })
        rel_list = []
        entity_map = {e.id: e.name for e in entities}
        for r in relations:
            rel_list.append({
                "from": entity_map.get(r.from_entity_id, "?"),
                "to": entity_map.get(r.to_entity_id, "?"),
                "name": r.name, "cardinality": r.cardinality,
            })
        result = {"entities": entity_list, "relations": rel_list}
        return result, f"本体模型: {len(entity_list)} 实体, {len(rel_list)} 关系", len(entity_list)

    def _tool_list_datasources(self, args: dict) -> tuple[Any, str, int]:
        svc = EntityDataService(self.db)
        assets = svc.list_assets()
        return assets, f"返回 {len(assets)} 个已启用数据资产", len(assets)

    def _tool_get_table_schema(self, args: dict) -> tuple[Any, str, int]:
        asset_name = str(args.get("datasource_name", "") or args.get("asset_name", "")).strip()
        table_name = str(args.get("table_name", "")).strip()
        if not asset_name:
            return {"error": "需要提供 asset_name（或 datasource_name）"}, "参数不完整", 0
        svc = EntityDataService(self.db)
        columns = svc.get_table_schema_for_asset(asset_name, table_name)
        if isinstance(columns, dict) and "error" in columns:
            return columns, columns["error"], 0
        tbl = table_name or asset_name
        return {"table": tbl, "columns": columns}, f"表 {tbl} 共 {len(columns)} 列", len(columns)

    def _tool_query_datasource(self, args: dict) -> tuple[Any, str, int]:
        asset_name = str(args.get("datasource_name", "") or args.get("asset_name", "")).strip()
        sql = str(args.get("sql", "")).strip()
        if not asset_name or not sql:
            return {"error": "需要提供 asset_name（或 datasource_name）和 sql"}, "参数不完整", 0
        svc = EntityDataService(self.db)
        result = svc.execute_sql_on_asset(asset_name, sql, purpose="agent.query_datasource")
        if "error" in result:
            return result, f"查询失败: {result['error']}", 0
        return result, f"查询返回 {result.get('rowCount', 0)} 行", result.get("rowCount", 0)

    def _tool_get_entity_detail(self, args: dict) -> tuple[Any, str, int]:
        entity_name = str(args.get("entity_name", "")).strip()
        if not entity_name:
            return {"error": "需要提供 entity_name"}, "参数不完整", 0
        entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        if not entity:
            return {"error": f"实体 '{entity_name}' 不存在"}, "实体不存在", 0
        attrs = [{"name": a.name, "type": a.type, "description": a.description, "required": a.required} for a in entity.attributes]
        rels_from = self.db.query(EntityRelation).filter(EntityRelation.from_entity_id == entity.id).all()
        rels_to = self.db.query(EntityRelation).filter(EntityRelation.to_entity_id == entity.id).all()
        all_entities = {e.id: e.name for e in self.db.query(OntologyEntity).all()}
        relations = []
        for r in rels_from:
            relations.append({"direction": "out", "name": r.name, "target": all_entities.get(r.to_entity_id, "?"), "cardinality": r.cardinality})
        for r in rels_to:
            relations.append({"direction": "in", "name": r.name, "source": all_entities.get(r.from_entity_id, "?"), "cardinality": r.cardinality})
        rules = []
        result = {
            "name": entity.name, "name_cn": entity.name_cn, "tier": entity.tier,
            "description": entity.description or "",
            "attributes": attrs, "relations": relations,
        }
        return result, f"返回实体 {entity.name_cn} 的详情", 1

    def _tool_query_entity_data(self, args: dict) -> tuple[Any, str, int]:
        """通过本体实体名查询真实实例数据，自动解析数据源"""
        entity_name = str(args.get("entity_name", "")).strip()
        filters = args.get("filters") or {}
        fields = args.get("fields") or []
        limit = min(int(args.get("limit", 20)), 200)

        entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        if not entity:
            return {"error": f"本体中不存在实体 '{entity_name}'"}, "实体不存在", 0

        valid_attrs = {a.name for a in entity.attributes}
        svc = EntityDataService(self.db)
        result = svc.query_entity_data(
            entity.id,
            filters=filters,
            fields=fields,
            limit=limit,
            purpose="agent.query_entity_data",
            valid_attrs=valid_attrs,
        )
        if "error" in result:
            return result, f"查询失败: {result['error']}", 0

        result["entity"] = entity_name
        result["entity_cn"] = entity.name_cn
        return result, f"通过本体 {entity.name_cn} 查询到 {result.get('rowCount', 0)} 条记录", result.get("rowCount", 0)

    def _tool_execute_action(self, args: dict) -> tuple[Any, str, int]:
        action_name = str(args.get("action_name", "")).strip()
        params = args.get("params", {})
        dry_run = args.get("dry_run", True)
        if not action_name:
            return {"error": "需要提供 action_name"}, "参数不完整", 0

        from app.models.action import EntityAction
        action = self.db.query(EntityAction).filter(
            EntityAction.name == action_name,
            EntityAction.status == "active",
        ).first()
        if not action:
            return {"error": f"动作 '{action_name}' 不存在或未激活"}, f"动作 '{action_name}' 不存在", 0

        try:
            result = run_executor_sync(action.action_type, action.type_config or {}, params, dry_run)
            result_dict = {
                "action_name": action_name,
                "success": result.success,
                "message": result.message,
                "effects": result.output or {},
            }
            mode = "模拟执行" if dry_run else "执行"
            summary = f"{mode} '{action_name}' {'成功' if result.success else '失败'}"
            return result_dict, summary, 1
        except Exception as e:
            return {"error": str(e)}, f"执行失败: {e}", 0

    # ── 本体构建器（chat 模式）三件套 ────────────────────────────

    def _tool_list_business_datasources(self, args: dict) -> tuple[Any, str, int]:
        """召回结构化资产候选（Asset.kind in ['table','sql_view']）。

        M2.2 改造：底层从 DataSource 表切换到 Asset Catalog（按 kind 过滤）。
        前端 display_card.kind="datasource" 仍渲染到「结构化资产」栏，
        返回字段保持兼容（id/name/description/sample_tables 等）。
        """
        from app.models.asset import Asset

        domain = str(args.get("domain", "")).strip()
        keywords = args.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []

        rows = (
            self.db.query(Asset)
            .filter(Asset.status == "active",
                    Asset.kind.in_(["table", "sql_view"]))
            .all()
        )

        def matches(a: Asset) -> bool:
            blob = " ".join(filter(None, [
                a.name or "", a.alias or "", a.description or "",
                a.domain or "", " ".join(a.tags or []),
                ((a.locator or {}).get("table") or ""),
            ])).lower()
            if domain and domain.lower() not in blob:
                return False
            if keywords:
                return any(str(k).lower() in blob for k in keywords)
            return True

        items = []
        for a in rows:
            if not matches(a):
                continue
            sample_tables: list[str] = []
            loc = a.locator or {}
            if a.kind == "table" and loc.get("table"):
                sample_tables = [loc["table"]]
            elif a.kind == "sql_view":
                sample_tables = list(loc.get("dependencies") or [])[:3]
            items.append({
                "id": a.id, "name": a.name + (f" @{a.alias}" if a.alias else ""),
                "description": a.description or "",
                "table_count": len(sample_tables) or 1,
                "domain_tags": list(a.tags or []),
                "sample_tables": sample_tables[:3],
                "kind": a.kind,
            })

        result = {
            "items": items,
            "display_card": {
                "type": "asset_picker",
                "kind": "datasource",
                "title": f"为「{domain or '该业务'}」匹配到 {len(items)} 个结构化资产",
                "items": items,
            },
        }
        return result, f"匹配 {len(items)} 个结构化资产", len(items)

    def _tool_list_business_documents(self, args: dict) -> tuple[Any, str, int]:
        """召回非结构化资产候选（Asset.kind='document'）。

        M2.2 改造：底层从 BusinessDocument 表切换到 Asset Catalog（kind=document，
        含 file/oss/directory/api/mq 各 source_type）。返回字段保持兼容。
        """
        from app.models.asset import Asset

        domain = str(args.get("domain", "")).strip()
        ds_ids = args.get("datasource_ids") or []
        rows = (
            self.db.query(Asset)
            .filter(Asset.status == "active", Asset.kind == "document")
            .all()
        )

        def matches(a: Asset) -> bool:
            if not domain:
                return True
            tags = " ".join(a.tags or [])
            blob = f"{a.name or ''} {tags} {(a.parsed_summary or '')[:1000]} {a.description or ''}".lower()
            return domain.lower() in blob

        items = []
        for a in rows:
            if not matches(a):
                continue
            loc = a.locator or {}
            file_type = loc.get("file_type") or a.document_source_type or ""
            size_bytes = 0  # Asset 模型未保存原始 size；前端展示位
            items.append({
                "id": a.id, "name": a.name, "file_type": file_type,
                "size_bytes": size_bytes,
                "domain_tags": list(a.tags or []),
                "summary": (a.parsed_summary or "")[:1000],
                "source_type": a.document_source_type,
            })

        result = {
            "items": items,
            "linked_datasource_ids": list(ds_ids) if isinstance(ds_ids, list) else [],
            "display_card": {
                "type": "asset_picker",
                "kind": "document",
                "title": f"为「{domain or '该业务'}」匹配到 {len(items)} 份非结构化资产",
                "items": items,
            },
        }
        return result, f"匹配 {len(items)} 份非结构化资产", len(items)

    def _tool_analyze_assets_for_ontology(self, args: dict) -> tuple[Any, str, int]:
        """根据已选结构化资产 + 非结构化资产 + 业务上下文，让 LLM 抽取本体草稿。

        M2.2 改造：
        - 输入参数 datasource_ids / document_ids 都按 Asset.id 处理（兼容老 id：通过
          legacy_datasource_id / legacy_business_document_id 反查）。
        - 输出强制带 backing_asset_ids（每个 entity）+ source_asset_id / source_column（每个 property），
          让前端 Step1Build.confirmAll 能直接落地，省掉一次手工映射。
        """
        import json as _json
        import re as _re

        from app.config import settings as _settings
        from app.services.copilot import get_llm_client

        ds_ids = args.get("datasource_ids") or []
        doc_ids = args.get("document_ids") or []
        ctx = str(args.get("business_context") or "").strip()

        # 1. 解析 Asset（兼容老 id）
        table_assets = self._resolve_assets(ds_ids, kinds=("table", "sql_view"))
        doc_assets = self._resolve_assets(doc_ids, kinds=("document",))

        # 2. 拼结构化资产 schema
        ds_blocks: list[str] = []
        for a in table_assets:
            cols = a.schema_snapshot or []
            col_lines = "\n".join(
                f"  - {c.get('name')} ({c.get('type','?')}){' PK' if c.get('is_pk') else ''}: {c.get('comment') or ''}"
                for c in cols[:30]
            )
            tname = (a.locator or {}).get("table") or a.alias or a.name
            ds_blocks.append(f"### Asset {a.name} (id={a.id}) · 表 {tname}\n{col_lines}")

        # 3. 拼文档正文
        doc_blocks: list[str] = []
        for a in doc_assets:
            doc_blocks.append(f"### 文档 {a.name} (id={a.id})\n{(a.parsed_summary or '')[:6000]}")

        prompt = """你是本体建模专家，要从用户提供的资产 schema + 业务文档中抽取本体草稿。
术语规范：对象（Object）/ 属性（Property）/ 关系（Relation）/ 规则（Rule）/ 动作（Action）。

严格返回 JSON：
{
  "entities": [{"name":"PascalCase","display_name":"中文","tier":1|2|3,"description":"...","primary_key":"id","icon":"emoji","properties":[{"name":"snake_case","display_name":"中文","type":"string|number|date|boolean|enum","required":true|false,"description":"..."}]}],
  "relations": [{"name":"snake_case","display_name":"中文","from_entity":"对象英文名","to_entity":"对象英文名","cardinality":"1:1|1:N|N:N","description":"..."}],
  "suggested_rules": [{"name":"中文","description":"...","condition_hint":"...","action_hint":"...","target_entity":"对象英文名"}],
  "suggested_actions": [{"name":"中文","description":"...","trigger_hint":"...","effect_hint":"...","target_entity":"对象英文名"}]
}
不要输出其他文字。
"""
        user_content = (
            f"## 业务上下文\n{ctx or '（无）'}\n\n"
            f"## 结构化资产 Schema\n" + ("\n\n".join(ds_blocks) or "（无）") + "\n\n"
            f"## 非结构化资产\n" + ("\n\n".join(doc_blocks) or "（无）")
        )[:18000]

        client = get_llm_client()
        try:
            resp = client.chat.completions.create(
                model=_settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0,
                max_tokens=6000,
                timeout=120,
            )
        except Exception as e:
            return {"error": f"LLM 调用失败: {e}"}, f"LLM 调用失败", 0

        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = _re.sub(r"^```\w*\n", "", text)
            text = _re.sub(r"\n```\s*$", "", text)
        try:
            data = _json.loads(text)
        except _json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end < 0:
                return {"error": "LLM 返回不是合法 JSON"}, "解析失败", 0
            data = _json.loads(text[start: end + 1])

        ents = data.get("entities", []) or []
        rels = data.get("relations", []) or []
        s_rules = data.get("suggested_rules", []) or []
        s_actions = data.get("suggested_actions", []) or []

        # 4. 关键：自动回写 backing_asset_ids + source_asset_id + source_column
        for ent in ents:
            asset_for_ent = self._guess_backing_asset(ent, table_assets)
            ent["backing_asset_ids"] = [asset_for_ent.id] if asset_for_ent else [a.id for a in table_assets]
            ent["evidence_asset_ids"] = [a.id for a in doc_assets]
            for prop in (ent.get("properties") or []):
                src_asset, src_col = self._guess_source(prop, table_assets)
                prop["source_asset_id"] = src_asset.id if src_asset else None
                prop["source_column"] = src_col

        result = {
            "entities": ents,
            "relations": rels,
            "suggested_rules": s_rules,
            "suggested_actions": s_actions,
        }
        summary = f"产出 {len(ents)} 对象 / {len(rels)} 关系 / {len(s_rules)} 规则建议 / {len(s_actions)} 动作建议（已自动绑定 backing）"
        return result, summary, len(ents)

    # ── Tier 1: 数据查询（重构） ────────────────────────────────

    def _tool_query_instances(self, args: dict) -> tuple[Any, str, int]:
        entity_name = str(args.get("entity_name", "")).strip()
        filters = args.get("filters") or {}
        page = int(args.get("page", 1))
        page_size = min(int(args.get("page_size", 50)), 200)
        if not entity_name:
            return {"error": "需要提供 entity_name"}, "参数不完整", 0

        entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        if not entity:
            return {"error": f"本体中不存在实体 '{entity_name}'"}, "实体不存在", 0

        valid_attrs = {a.name for a in entity.attributes}
        svc = EntityDataService(self.db)
        result = svc.query_entity_data(
            entity.id, filters=filters, fields=[], limit=page_size,
            purpose="agent.query_instances", valid_attrs=valid_attrs,
        )
        if "error" in result:
            return result, f"查询失败: {result['error']}", 0
        result["entity"] = entity_name
        result["page"] = page
        return result, f"查询 {entity.name_cn} 第{page}页，返回 {result.get('rowCount', 0)} 条", result.get("rowCount", 0)

    def _tool_get_attr_mapping(self, args: dict) -> tuple[Any, str, int]:
        entity_names = args.get("entity_names", [])
        if not entity_names:
            return {"error": "需要提供 entity_names"}, "参数不完整", 0

        mapping = {}
        for name in entity_names:
            entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == name).first()
            if not entity:
                mapping[name] = {"error": f"实体 '{name}' 不存在"}
                continue
            svc = EntityDataService(self.db)
            resolved = svc.resolve_entity_asset(entity.id)
            if not resolved:
                mapping[name] = {"error": "未绑定数据源"}
                continue
            asset, binding = resolved
            table_name = svc.get_table_name(asset)
            attrs = {}
            for a in entity.attributes:
                attrs[a.name] = a.source_field or a.name
            mapping[name] = {"table": table_name, "attributes": attrs}
        return mapping, f"返回 {len(entity_names)} 个实体的映射", len(entity_names)

    def _tool_complex_sql(self, args: dict) -> tuple[Any, str, int]:
        sql = str(args.get("sql", "")).strip()
        if not sql:
            return {"error": "需要提供 sql"}, "参数不完整", 0
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            return {"error": "只允许 SELECT/WITH 语句"}, "非法 SQL", 0
        if ";" in sql:
            return {"error": "不允许多语句查询"}, "非法 SQL", 0

        svc = EntityDataService(self.db)
        # 以本体对象名书写 SQL：重写对象名→物理表名，并把涉及的 asset 全部并入白名单
        entities = self.db.query(OntologyEntity).all()
        if not entities:
            return {"error": "没有可用对象"}, "无数据源", 0
        result = svc.execute_ontology_sql(entities, sql, purpose="agent.complex_sql")
        if "error" in result:
            return result, f"SQL 执行失败: {result['error']}", 0
        return result, f"SQL 查询返回 {result.get('rowCount', 0)} 行", result.get("rowCount", 0)

    # ── Tier 2: 逻辑/动作调用 ──────────────────────────────────

    def _tool_list_capabilities(self, args: dict) -> tuple[Any, str, int]:
        if not self.runtime_executor:
            return {"error": "Function runtime not initialized"}, "运行时未就绪", 0
        type_filter = args.get("type", "all")
        caps = self.runtime_executor.registry.list_capabilities()
        if type_filter != "all":
            caps = [c for c in caps if c["type"] == type_filter]
        return caps, f"找到 {len(caps)} 个可用函数", len(caps)

    def _tool_run_logic(self, args: dict) -> tuple[Any, str, int]:
        if not self.runtime_executor:
            return {"error": "Function runtime not initialized"}, "运行时未就绪", 0
        callable_name = args.get("callable_name", "")
        params = args.get("params", {})
        meta = self.runtime_executor.registry.get(callable_name)
        if meta and meta.type != "logic":
            return {"success": False, "error": f"'{callable_name}' 类型为 {meta.type}，不是 logic"}, "类型不匹配", 0
        result = self.runtime_executor.execute(callable_name, params)
        return {
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "execution_ms": result.execution_ms,
            "call_trace": result.call_trace,
        }, f"逻辑函数{'成功' if result.success else '失败'}: {callable_name}", 1

    def _tool_run_action(self, args: dict) -> tuple[Any, str, int]:
        if not self.runtime_executor:
            return {"error": "Function runtime not initialized"}, "运行时未就绪", 0
        callable_name = args.get("callable_name", "")
        params = args.get("params", {})
        meta = self.runtime_executor.registry.get(callable_name)
        if meta and meta.type != "action":
            return {"success": False, "error": f"'{callable_name}' 类型为 {meta.type}，不是 action"}, "类型不匹配", 0
        result = self.runtime_executor.execute(callable_name, params)
        return {
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "execution_ms": result.execution_ms,
            "call_trace": result.call_trace,
        }, f"动作函数{'成功' if result.success else '失败'}: {callable_name}", 1

    # ── 启发式：guess backing / source 列 ────────────────────

    def _resolve_assets(self, ids: list, *, kinds: tuple[str, ...]) -> list:
        """把 ids（可能是 Asset.id 也可能是老 DataSource.id 或 BusinessDocument.id）
        全部解析到 Asset 实例。"""
        from app.models.asset import Asset
        out: list[Asset] = []
        seen: set[str] = set()
        for raw_id in ids or []:
            a = self.db.get(Asset, raw_id) if raw_id else None
            if not a:
                a = (self.db.query(Asset)
                     .filter((Asset.legacy_datasource_id == raw_id)
                             | (Asset.legacy_business_document_id == raw_id))
                     .first())
            if a and a.kind in kinds and a.id not in seen:
                out.append(a)
                seen.add(a.id)
        return out

    @staticmethod
    def _normalize_name(s: str) -> str:
        return (s or "").lower().replace("_", "").replace("-", "")

    def _guess_backing_asset(self, entity: dict, candidates: list):
        """启发式选最可能 backing 这个 entity 的资产。

        简单规则：name 与 alias / table 名 / 资产名 normalize 后字符串相似度最高的。
        无明显匹配返回 None（让前端用 candidates 第一个或人工选）。
        """
        ent_n = self._normalize_name(entity.get("name", ""))
        if not ent_n or not candidates:
            return None
        best = None
        best_score = 0.0
        for a in candidates:
            target = self._normalize_name(
                (a.locator or {}).get("table") or a.alias or a.name or ""
            )
            if not target:
                continue
            score = self._sim(ent_n, target)
            if score > best_score:
                best, best_score = a, score
        return best if best_score >= 0.5 else None

    def _guess_source(self, prop: dict, candidates: list):
        """启发式：找 prop.name 对应的 (asset, column)。"""
        prop_n = self._normalize_name(prop.get("name", ""))
        if not prop_n or not candidates:
            return None, None
        best_asset = None
        best_col = None
        best_score = 0.0
        for a in candidates:
            for c in (a.schema_snapshot or []):
                cname = c.get("name", "")
                score = self._sim(prop_n, self._normalize_name(cname))
                if score > best_score:
                    best_score = score
                    best_asset = a
                    best_col = cname
        if best_score >= 0.6:
            return best_asset, best_col
        return None, None

    @staticmethod
    def _sim(a: str, b: str) -> float:
        """SequenceMatcher 比 ratio 简单封装。"""
        if not a or not b:
            return 0.0
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a, b).ratio()
