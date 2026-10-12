"""Write actual business instances through a reviewed ObjectBinding and write gate."""
from __future__ import annotations

import re

from app.connectors import ConnectorRegistry
from app.models.connection import Connection
from app.models.entity import OntologyEntity
from app.services.data_plane.entity_data_service import EntityDataService
from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService, ExecuteOutcomeUnknown


class ObjectMutationService:
    def __init__(self, db, version_entity=None):
        self.db = db
        self.version_entity = version_entity
        if version_entity:
            from app.services.version_entity_data import VersionEntityDataService
            self.data = VersionEntityDataService(db, version_entity)
        else:
            self.data = EntityDataService(db)
        self.execute = ExecuteService(db)

    def _resolve(self, entity_id, *, require_write=True):
        if self.version_entity and self.version_entity.source_entity_id != entity_id:
            raise PermissionError("行动目标不属于当前发布对象")
        entity = self.version_entity or self.db.get(OntologyEntity, entity_id)
        if not entity:
            raise ValueError("目标对象不存在")
        resolved = self.data.resolve_entity_asset(entity_id)
        if not resolved:
            raise ValueError("目标对象没有可执行的主资产绑定")
        asset, binding = resolved
        if binding.status != "active" or asset.kind != "table":
            raise ValueError("只能写入状态正常的表资产绑定")
        connection = self.db.get(Connection, asset.connection_id)
        if not connection or not connection.enabled or (require_write and not connection.writable):
            raise PermissionError("目标数据源未允许写入")
        fields = self.data.get_attr_field_map(entity_id)
        attrs = {a.name: a for a in entity.attributes}
        pk = binding.id_column or (asset.primary_key[0] if len(asset.primary_key or []) == 1 else None)
        id_attrs = [name for name, column in fields.items() if column == pk]
        if not pk or len(id_attrs) != 1:
            raise ValueError("必须配置且映射唯一的实例 ID 列")
        quote = ConnectorRegistry.get(connection.type).quote_identifier()
        def quoted(identifier):
            if not identifier or not re.fullmatch(r"[\w]+", identifier):
                raise ValueError(f"无效数据字段标识符: {identifier}")
            return f"{quote}{identifier}{quote}"
        return entity, asset, binding, fields, attrs, id_attrs[0], quoted

    def _validated(self, values, attrs, fields):
        from app.services.agent_actions import validate_parameters
        if not isinstance(values, dict) or not values:
            raise ValueError("写入内容不能为空")
        if set(values) - set(attrs):
            raise ValueError(f"未知对象属性: {', '.join(set(values) - set(attrs))}")
        definitions = [{"name": name, "type": attr.type, "required": attr.required,
                        "enum": (attr.constraints_json or {}).get("enum")}
                       for name, attr in attrs.items() if name in values]
        validated = validate_parameters(definitions, values)
        for name in validated:
            if name not in fields:
                raise ValueError(f"属性 {name} 没有可写字段映射")
            if validated[name] is None and attrs[name].required:
                raise ValueError(f"必填属性 {name} 不能为空")
        return validated

    def _readonly_transforms(self, entity_id, binding):
        attribute_names = self.data.get_query_attribute_names(entity_id)
        bindings = [binding] + [extra for _, extra in self.data.resolve_entity_enrichments(entity_id)]
        return {attribute_names.get(mapping.get("attribute_id"))
                for source in bindings for mapping in source.field_mappings or []
                if mapping.get("transform")}

    def update(self, entity_id, record_id, updates, *, user_id=None):
        entity, asset, binding, fields, attrs, id_attr, quoted = self._resolve(entity_id, require_write=False)
        if record_id is None:
            raise ValueError("必须指定实例 record_id")
        if id_attr in updates:
            raise ValueError("不能通过修改属性改变实例 ID")
        readonly = set(updates) & self._readonly_transforms(entity_id, binding)
        if readonly:
            raise ValueError("transform 结果属性为只读，未执行写入: " + ", ".join(sorted(readonly)))
        selected_asset, selected_binding = asset, binding
        target_fields = dict(fields)
        attr_names = self.data.get_query_attribute_names(entity_id)
        sources = {name: (asset, binding, False) for name in fields}
        for extra_asset, extra_binding in self.data.resolve_entity_enrichments(entity_id):
            for mapping in extra_binding.field_mappings or []:
                name = attr_names.get(mapping.get("attribute_id"))
                if name and not mapping.get("transform"):
                    if name in sources:
                        raise ValueError(f"属性 {name} 在多个数据源映射，拒绝不确定写入")
                    sources[name] = (extra_asset, extra_binding, True)
                    target_fields[name] = mapping.get("source_column")
        values = self._validated(updates, attrs, target_fields)
        selected_sources = {sources[name][0].id for name in values if sources[name][0]}
        if len(selected_sources) != 1:
            raise ValueError("一次写入只能修改同一资产的属性；跨数据源原子写入尚未定义，未执行任何修改")
        selected_asset, selected_binding, enriched = sources[next(iter(values))]
        if not selected_asset or selected_asset.status != "active" or selected_asset.kind != "table" or selected_binding.status != "active":
            raise ValueError("目标属性的资产绑定已失效或尚未审核")
        selected_connection = self.db.get(Connection, selected_asset.connection_id)
        if not selected_connection or not selected_connection.enabled or not selected_connection.writable:
            raise PermissionError("目标属性数据源未允许写入")
        existing = self.data.query_entity_data(entity_id, filters={id_attr: record_id}, limit=2)
        if existing.get("error"):
            raise RuntimeError(existing["error"])
        if len(existing.get("rows", [])) != 1:
            raise ValueError("实例不存在或 ID 非唯一，拒绝写入")
        target_key, target_value = fields[id_attr], record_id
        if enriched:
            primary_column = selected_binding.primary_source_column
            target_key = selected_binding.enrichment_source_column
            if not primary_column or not target_key:
                raise ValueError("enrichment 写入必须配置明确的一对一关联字段")
            if target_key in {target_fields[name] for name in values}:
                raise ValueError("不能通过修改属性改变 enrichment 关联字段")
            key_data = self.data._query_primary_data(entity_id, filters={id_attr:record_id},
                fields=[id_attr,"_ontology_write_join"], _physical_fields={"_ontology_write_join":primary_column},limit=2)
            if key_data.get("error") or len(key_data.get("rows", [])) != 1:
                raise ValueError("无法唯一解析实例的 enrichment 关联值")
            target_value = key_data["rows"][0][key_data["columns"].index("_ontology_write_join")]
            if target_value is None:
                raise ValueError("实例没有 enrichment 关联值，未执行写入")
            self.data._assert_unique_join_key(selected_asset, selected_binding, target_key, purpose="object_instance_preflight")
            query = f"SELECT {self.data._quote(selected_asset,target_key)} FROM <asset> WHERE {self.data._quote(selected_asset,target_key)} = :record_id"
            if selected_binding.filter_expr:query += f" AND ({selected_binding.filter_expr})"
            matches = self.execute.execute(ExecuteRequest(selected_asset.id, query, {"record_id":target_value},
                purpose="object_instance_preflight", bypass_cache=True))
            if len(matches.rows) != 1:
                raise ValueError("关联 enrichment 实例不存在或非唯一，拒绝写入")
        params = {"record_id": target_value, **{f"value_{i}": value for i, value in enumerate(values.values())}}
        sets = [f"{self.data._quote(selected_asset,target_fields[name])} = :value_{i}" for i, name in enumerate(values)]
        sql = f"UPDATE <asset> SET {', '.join(sets)} WHERE {self.data._quote(selected_asset,target_key)} = :record_id"
        if selected_binding.filter_expr:
            sql += f" AND ({selected_binding.filter_expr})"
        ExecuteService.ALLOWED_WRITE_PURPOSES.add("object_instance_update")
        self.execute.execute(ExecuteRequest(selected_asset.id, sql, params, purpose="object_instance_update", user_id=user_id, bypass_cache=True))
        try:
            readback = self.data.query_entity_data(entity_id, filters={id_attr: record_id}, limit=2)
        except Exception as exc:
            raise ExecuteOutcomeUnknown("源写入已提交但回读失败，禁止自动重试") from exc
        if readback.get("error") or len(readback.get("rows", [])) != 1:
            raise ExecuteOutcomeUnknown("数据写入后回读失败，结果需要核对，禁止自动重试")
        row = dict(zip(readback["columns"], readback["rows"][0]))
        return {"entity_id": entity_id, "record_id": record_id, "instance": row, "outcome": "committed"}

    def create(self, entity_id, values, *, user_id=None):
        entity, asset, binding, fields, attrs, id_attr, quoted = self._resolve(entity_id)
        readonly = set(values) & self._readonly_transforms(entity_id, binding)
        if readonly:
            raise ValueError("transform 结果属性为只读，未执行写入: " + ", ".join(sorted(readonly)))
        values = self._validated(values, attrs, fields)
        missing = [a.name for a in attrs.values() if a.required and a.name not in values]
        if missing or id_attr not in values:
            raise ValueError(f"缺少必填实例属性: {', '.join(missing or [id_attr])}")
        exists = self.data.query_entity_data(entity_id, filters={id_attr: values[id_attr]}, limit=1)
        if exists.get("error"):
            raise RuntimeError(exists["error"])
        if exists.get("rows"):
            raise ValueError("实例 ID 已存在")
        sql = f"INSERT INTO <asset> ({', '.join(quoted(fields[k]) for k in values)}) VALUES ({', '.join(':value_' + str(i) for i in range(len(values)))})"
        params = {f"value_{i}": value for i, value in enumerate(values.values())}
        ExecuteService.ALLOWED_WRITE_PURPOSES.add("object_instance_create")
        self.execute.execute(ExecuteRequest(asset.id, sql, params, purpose="object_instance_create", user_id=user_id, bypass_cache=True))
        try:
            result = self.data.query_entity_data(entity_id, filters={id_attr: values[id_attr]}, limit=1)
        except Exception as exc:
            raise ExecuteOutcomeUnknown("源创建已提交但回读失败，禁止自动重试") from exc
        if result.get("error") or not result.get("rows"):
            raise ExecuteOutcomeUnknown("数据创建后回读失败，结果需要核对，禁止自动重试")
        return dict(zip(result["columns"], result["rows"][0]))
