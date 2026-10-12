"""HydrationService — 水合演练：验证本体草稿与真实数据的映射。

4 阶段流式验证，每阶段 yield SSE event dict：
1. ingest     — 连接验证 + schema 同步 + preview + profile
2. instantiate — 属性 ↔ 列映射验证（启发式打分）
3. match      — 关系 JOIN key 验证 + 样本 JOIN
4. strategy   — PK 唯一性 + 必填字段空值率
"""
from __future__ import annotations

import logging
import time
from collections.abc import Generator

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.repositories.asset_repo import AssetRepository
from app.services.data_plane.asset_service import AssetService
from app.services.data_plane.connection_service import ConnectionService
from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService

logger = logging.getLogger(__name__)


# ── 请求模型 ──────────────────────────────────────────────────────

class HydrateProperty(BaseModel):
    name: str
    displayName: str | None = None
    type: str = "string"
    required: bool = False
    source_asset_id: str | None = None
    source_column: str | None = None
    transform: str | None = None
    source_field: str | None = None
    source_table: str | None = None


class HydrateEnrichment(BaseModel):
    asset_id: str
    primary_source_column: str | None = None
    enrichment_source_column: str | None = None


class HydrateObject(BaseModel):
    name: str
    displayName: str | None = None
    tier: int = 2
    primaryKey: str | None = None
    properties: list[HydrateProperty] = []
    backing_asset_ids: list[str] = []
    enrichment_bindings: list[HydrateEnrichment] = []


class HydrateRelation(BaseModel):
    name: str
    displayName: str | None = None
    source: str
    target: str
    cardinality: str = "1:N"
    sourceField: str | None = None
    targetField: str | None = None


class HydrationRequest(BaseModel):
    session_id: str
    objects: list[HydrateObject]
    relations: list[HydrateRelation]
    asset_ids: list[str]


# ── 服务 ──────────────────────────────────────────────────────────

class HydrationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.asset_svc = AssetService(db)
        self.conn_svc = ConnectionService(db)
        self.exec_svc = ExecuteService(db)
        self.asset_repo = AssetRepository(db)

    def run(self, req: HydrationRequest) -> Generator[dict, None, None]:
        """编排 4 阶段水合验证，逐事件 yield。"""
        phase_results: list[dict] = []
        total_rows = 0
        total_cols = 0
        loaded_assets = 0
        asset_cache: dict[str, Asset] = {}  # asset_id -> Asset
        asset_rows: dict[str, int] = {}

        req.asset_ids = list(dict.fromkeys([
            *req.asset_ids, *(aid for obj in req.objects for aid in obj.backing_asset_ids),
        ]))
        # ── 前置校验：没有任何可用资产则直接快速失败 ──────────
        has_backing = any(obj.backing_asset_ids for obj in req.objects)
        if not req.asset_ids and not has_backing:
            yield {"type": "phase_log", "phase": "ingest", "level": "ERR",
                   "msg": "未找到可用数据资产，请先在「资产目录」中注册数据表，或在对象上绑定 backing asset"}
            yield {
                "type": "drill_complete",
                "result": {
                    "phases": [{
                        "key": "ingest", "label": "数据接入", "status": "error",
                        "metrics": [{"label": "装载资产数", "value": "0/0", "tone": "warn"}],
                    }],
                    "logs": [],
                    "selectedRows": 0, "selectedColumns": 0, "selectedSources": 0,
                    "entityCount": 0, "relationCount": 0,
                    "attributionAccuracy": "N/A",
                    "highConfidenceAttribution": 0, "manualReview": 0,
                },
                "status": "error",
            }
            return

        # ── Phase 1: 数据接入 ─────────────────────────────
        yield {"type": "phase_progress", "phase": "ingest", "progress": 0}
        ingest_start = time.time()
        ingest_status = "pass"

        for aid in req.asset_ids:
            asset = self.asset_svc.get(aid)
            if not asset:
                msg = f"资产不存在: {aid}"
                yield {"type": "phase_log", "phase": "ingest", "level": "ERR", "msg": msg}
                ingest_status = "error"
                continue

            if asset.status != "active":
                ingest_status = "error"
                yield {"type": "phase_log", "phase": "ingest", "level": "ERR", "msg": f"资产已失效: {asset.name}"}
                continue
            asset_cache[aid] = asset
            conn_id = asset.connection_id

            # 测试连接
            if conn_id:
                try:
                    result = self.conn_svc.test(conn_id)
                    if result.get("success"):
                        lat = result.get("latency_ms", 0)
                        yield {"type": "phase_log", "phase": "ingest", "level": "OK",
                               "msg": f"连接 {asset.name} 成功 ({lat}ms)"}
                    else:
                        yield {"type": "phase_log", "phase": "ingest", "level": "ERR",
                               "msg": f"连接 {asset.name} 失败: {result.get('message', '')}"}
                        ingest_status = "error"
                        continue
                except Exception as e:
                    yield {"type": "phase_log", "phase": "ingest", "level": "ERR",
                           "msg": f"连接 {asset.name} 异常: {e}"}
                    ingest_status = "error"
                    continue

            # sync_schema
            try:
                schema_result = self.asset_svc.sync_schema(aid)
                cols = schema_result.get("schema_snapshot", [])
                col_count = len(cols)
                total_cols += col_count
                yield {"type": "phase_log", "phase": "ingest", "level": "OK",
                       "msg": f"sync_schema: {asset.name} {col_count} 列"}
            except Exception as e:
                yield {"type": "phase_log", "phase": "ingest", "level": "ERR",
                       "msg": f"sync_schema {asset.name} 失败: {e}"}
                ingest_status = "error"

            # preview
            try:
                preview = self.asset_svc.preview(aid, limit=10)
                rows_returned = preview.get("rows_returned", 0)
                yield {"type": "phase_log", "phase": "ingest", "level": "OK",
                       "msg": f"preview: {asset.name} {rows_returned} 行样例已加载"}
            except Exception as e:
                yield {"type": "phase_log", "phase": "ingest", "level": "ERR",
                       "msg": f"preview {asset.name} 失败: {e}"}
                ingest_status = "error"

            # profile
            try:
                profile = self.asset_svc.profile(aid)
                row_count = profile.get("row_count", 0)
                asset_rows[aid] = row_count
                total_rows += row_count
                yield {"type": "phase_log", "phase": "ingest", "level": "OK",
                       "msg": f"profile: {asset.name} {row_count:,} 行, 列空值率已计算"}
            except Exception as e:
                yield {"type": "phase_log", "phase": "ingest", "level": "ERR",
                       "msg": f"profile {asset.name} 失败: {e}"}
                ingest_status = "error"

            loaded_assets += 1

        ingest_elapsed = round(time.time() - ingest_start, 1)
        yield {"type": "phase_progress", "phase": "ingest", "progress": 0.25}
        yield {
            "type": "phase_complete", "phase": "ingest", "status": ingest_status,
            "metrics": [
                {"label": "装载资产数", "value": f"{loaded_assets}/{len(req.asset_ids)}",
                 "tone": "pass" if loaded_assets == len(req.asset_ids) else "warn"},
                {"label": "总列数", "value": str(total_cols)},
                {"label": "总行数", "value": f"{total_rows:,}"},
                {"label": "装载耗时", "value": f"{ingest_elapsed}s"},
            ],
        }
        phase_results.append({"key": "ingest", "label": "数据接入", "status": ingest_status,
                              "metrics": [
                                  {"label": "装载资产数", "value": f"{loaded_assets}/{len(req.asset_ids)}"},
                                  {"label": "总列数", "value": str(total_cols)},
                                  {"label": "总行数", "value": f"{total_rows:,}"},
                                  {"label": "装载耗时", "value": f"{ingest_elapsed}s"},
                              ]})

        # ── Phase 2: 本体实例化 ───────────────────────────
        yield {"type": "phase_progress", "phase": "instantiate", "progress": 0.3}
        instantiate_start = time.time()
        instantiate_status = "pass" if req.objects else "error"
        total_props = 0
        matched_props = 0
        high_confidence_props = 0
        unmatched_props: list[str] = []

        # 如果没有任何可用资产 schema，直接跳过逐属性匹配
        _skip_instantiate = not asset_cache
        if _skip_instantiate:
            yield {"type": "phase_log", "phase": "instantiate", "level": "ERR",
                   "msg": "未找到可用数据资产，请先在「资产目录」中注册数据表，或在对象上绑定 backing asset"}
            instantiate_status = "error"
            total_props = sum(len(obj.properties) for obj in req.objects)

        _objs_to_check = [] if _skip_instantiate else req.objects
        for obj in _objs_to_check:
            obj_matched = 0
            obj_high_confidence = 0
            obj_total = len(obj.properties)
            total_props += obj_total

            effective_asset_ids = obj.backing_asset_ids
            if not effective_asset_ids or not obj_total:
                instantiate_status = "error"
                yield {"type":"phase_log", "phase":"instantiate", "level":"ERR", "msg":f"{obj.displayName or obj.name}: 必须明确绑定数据资产并定义属性"}
            for prop in obj.properties:
                column = prop.source_column or prop.source_field
                aid = prop.source_asset_id
                if not aid or aid not in effective_asset_ids or not column:
                    unmatched_props.append(f"{obj.name}.{prop.name}")
                    yield {"type":"phase_log", "phase":"instantiate", "level":"ERR", "msg":f"{obj.displayName or obj.name}.{prop.name}: 必须明确选择已绑定资产及字段；推荐结果尚未构成有效映射"}
                    continue
                asset = asset_cache.get(aid)
                if not asset or asset.status != "active" or not any(field.get("name") == column for field in asset.schema_snapshot or []):
                    unmatched_props.append(f"{obj.name}.{prop.name}")
                    yield {"type":"phase_log", "phase":"instantiate", "level":"ERR", "msg":f"{obj.displayName or obj.name}.{prop.name}: 指定列 {column} 不存在或资产不可用"}
                    continue
                if prop.transform:
                    try:
                        from app.services.data_plane.mapping_transform import validate_transform, apply_transform
                        validate_transform(prop.transform)
                        if prop.name == obj.primaryKey:
                            raise ValueError("主键属性不能配置 transform")
                        quote = self._quote(asset)
                        sample = self.exec_svc.execute(ExecuteRequest(
                            asset_id=aid, sql=f"SELECT {self._quoted(column, quote)} FROM <asset> LIMIT 100",
                            params={}, purpose="hydrate.transform_sample", bypass_cache=True,
                        ))
                        converted = [apply_transform(row[0], prop.transform) for row in sample.rows]
                        if prop.required and (not converted or any(value is None for value in converted)):
                            raise ValueError("转换后的必填属性抽样为空")
                        yield {"type":"phase_log", "phase":"instantiate", "level":"OK", "msg":f"{obj.name}.{prop.name}: transform 最多100行真实抽样通过 ({len(converted)}行)"}
                    except Exception as exc:
                        unmatched_props.append(f"{obj.name}.{prop.name}")
                        yield {"type":"phase_log", "phase":"instantiate", "level":"ERR", "msg":f"{obj.name}.{prop.name}: transform 验证失败 - {exc}"}
                        continue
                obj_matched += 1
                obj_high_confidence += 1
                yield {"type":"phase_log", "phase":"instantiate", "level":"OK", "msg":f"{obj.displayName or obj.name}.{prop.name}: → {asset.name}.{column} ✓"}

            matched_props += obj_matched
            high_confidence_props += obj_high_confidence
            obj_status = "pass" if obj_total and obj_matched == obj_total else "error"
            yield {"type": "phase_log", "phase": "instantiate", "level": "OK",
                   "msg": f"{obj.displayName or obj.name}: {obj_matched}/{obj_total} 属性映射命中"}

            if obj_status == "error":
                instantiate_status = "error"
            elif obj_status == "warn" and instantiate_status == "pass":
                instantiate_status = "warn"

        mapping_rate = f"{matched_props / total_props * 100:.1f}%" if total_props else "N/A"
        instantiate_elapsed = round(time.time() - instantiate_start, 1)
        yield {"type": "phase_progress", "phase": "instantiate", "progress": 0.5}
        yield {
            "type": "phase_complete", "phase": "instantiate", "status": instantiate_status,
            "metrics": [
                {"label": "字段映射命中", "value": f"{matched_props}/{total_props}",
                 "tone": "pass" if matched_props == total_props else "warn"},
                {"label": "映射命中率", "value": mapping_rate,
                 "tone": "pass" if matched_props == total_props else "warn"},
                {"label": "映射耗时", "value": f"{instantiate_elapsed}s"},
            ],
        }
        phase_results.append({"key": "instantiate", "label": "本体实例化", "status": instantiate_status,
                              "metrics": [
                                  {"label": "字段映射命中", "value": f"{matched_props}/{total_props}"},
                                  {"label": "映射命中率", "value": mapping_rate},
                                  {"label": "映射耗时", "value": f"{instantiate_elapsed}s"},
                              ]})

        # ── Phase 3: 关系映射验证 ─────────────────────────
        yield {"type": "phase_progress", "phase": "match", "progress": 0.55}
        match_status = "pass"
        matched_relations = 0
        relation_count = 0
        total_relations = len(req.relations)

        # 构建对象查找映射（支持 name 和 displayName 作为 key，兼容前端可能传 id 的情况）
        obj_map: dict[str, HydrateObject] = {}
        for o in req.objects:
            obj_map[o.name] = o
            if o.displayName and o.displayName not in obj_map:
                obj_map[o.displayName] = o

        for rel in req.relations:
            src_obj = obj_map.get(rel.source)
            tgt_obj = obj_map.get(rel.target)

            if not src_obj or not tgt_obj:
                yield {"type": "phase_log", "phase": "match", "level": "ERR",
                       "msg": f"关系 {rel.displayName or rel.name}: 源/目标对象不存在 ({rel.source} → {rel.target})"}
                match_status = "error"
                continue

            # Both endpoint assets and relation fields must be explicitly mapped.
            src_assets = src_obj.backing_asset_ids
            tgt_assets = tgt_obj.backing_asset_ids

            if not src_assets or not tgt_assets:
                yield {"type": "phase_log", "phase": "match", "level": "WARN",
                       "msg": f"关系 {rel.displayName or rel.name}: 无 backing 资产，跳过 JOIN 验证"}
                match_status = "error"
                continue

            if not rel.sourceField or not rel.targetField:
                yield {"type": "phase_log", "phase": "match", "level": "ERR", "msg": f"关系 {rel.displayName or rel.name}: 未确认源/目标关联字段"}
                match_status = "error"
                continue
            src_pk = self._mapped_column(src_obj, rel.sourceField)
            tgt_pk = self._mapped_column(tgt_obj, rel.targetField)

            src_has_pk = False
            tgt_has_pk = False

            if src_pk:
                src_asset = asset_cache.get(src_assets[0]) or self.asset_svc.get(src_assets[0])
                if src_asset and src_asset.schema_snapshot:
                    src_has_pk = any(c.get("name") == src_pk for c in src_asset.schema_snapshot)

            if tgt_pk:
                tgt_asset = asset_cache.get(tgt_assets[0]) or self.asset_svc.get(tgt_assets[0])
                if tgt_asset and tgt_asset.schema_snapshot:
                    tgt_has_pk = any(c.get("name") == tgt_pk for c in tgt_asset.schema_snapshot)

            if not src_has_pk:
                yield {"type": "phase_log", "phase": "match", "level": "WARN",
                       "msg": f"关系 {rel.displayName or rel.name}: 源主键 {src_pk} 在源表中未找到"}
            if not tgt_has_pk:
                yield {"type": "phase_log", "phase": "match", "level": "WARN",
                       "msg": f"关系 {rel.displayName or rel.name}: 目标主键 {tgt_pk} 在目标表中未找到"}

            # 如果同连接，尝试样本 JOIN
            src_asset_obj = asset_cache.get(src_assets[0]) or self.asset_svc.get(src_assets[0])
            tgt_asset_obj = asset_cache.get(tgt_assets[0]) or self.asset_svc.get(tgt_assets[0])

            if (src_asset_obj and tgt_asset_obj and
                    src_asset_obj.connection_id == tgt_asset_obj.connection_id and
                    src_pk and tgt_pk and src_has_pk and tgt_has_pk):
                try:
                    src_table = (src_asset_obj.locator or {}).get("table", "")
                    tgt_table = (tgt_asset_obj.locator or {}).get("table", "")
                    quote = self._quote(src_asset_obj)
                    join_sql = (
                        f"SELECT COUNT(*) AS cnt FROM {self._table_quoted(src_table, quote)} s "
                        f"JOIN {self._table_quoted(tgt_table, quote)} t "
                        f"ON s.{self._quoted(src_pk, quote)} = t.{self._quoted(tgt_pk, quote)}"
                    )
                    r = self.exec_svc.execute(ExecuteRequest(
                        asset_id=src_assets[0], sql=join_sql, params={},
                        purpose="hydrate.relation_check", bypass_cache=True,
                        additional_asset_ids=[tgt_assets[0]],
                    ))
                    cnt = int(r.rows[0][0]) if r.rows else 0
                    yield {"type": "phase_log", "phase": "match", "level": "OK",
                           "msg": f"关系 {rel.displayName or rel.name}: JOIN 验证通过, 匹配 {cnt:,} 行"}
                    matched_relations += 1
                    relation_count += cnt
                except Exception as e:
                    yield {"type": "phase_log", "phase": "match", "level": "WARN",
                           "msg": f"关系 {rel.displayName or rel.name}: JOIN 验证失败 - {e}"}
                    match_status = "error"
            elif src_asset_obj and tgt_asset_obj and src_asset_obj.connection_id != tgt_asset_obj.connection_id:
                try:
                    if not src_has_pk or not tgt_has_pk:
                        raise ValueError("关联字段不在实际源 schema 中")
                    source_counts = self._key_counts(src_asset_obj, src_pk)
                    target_counts = self._key_counts(tgt_asset_obj, tgt_pk)
                    cnt = sum(count * target_counts.get(key, 0) for key, count in source_counts.items())
                    yield {"type": "phase_log", "phase": "match", "level": "OK",
                           "msg": f"关系 {rel.displayName or rel.name}: 跨连接真实关联验证通过, 匹配 {cnt:,} 行"}
                    matched_relations += 1
                    relation_count += cnt
                except Exception as exc:
                    yield {"type": "phase_log", "phase": "match", "level": "ERR",
                           "msg": f"关系 {rel.displayName or rel.name}: 跨连接关联验证失败 - {exc}"}
                    match_status = "error"
            else:
                yield {"type": "phase_log", "phase": "match", "level": "WARN",
                       "msg": f"关系 {rel.displayName or rel.name}: 跳过 JOIN 验证 (资产信息不完整)"}
                match_status = "error"

        relation_accuracy = f"{matched_relations / total_relations * 100:.1f}%" if total_relations else "N/A"
        yield {"type": "phase_progress", "phase": "match", "progress": 0.75}
        yield {
            "type": "phase_complete", "phase": "match", "status": match_status,
            "metrics": [
                {"label": "关系实例数", "value": f"{relation_count:,}"},
                {"label": "关系验证通过率", "value": relation_accuracy,
                 "tone": "pass" if match_status == "pass" else "warn"},
                {"label": "匹配覆盖率", "value": f"{matched_relations}/{total_relations}",
                 "tone": "pass" if matched_relations == total_relations else "warn"},
            ],
        }
        phase_results.append({"key": "match", "label": "关系映射验证", "status": match_status,
                              "metrics": [
                                  {"label": "关系实例数", "value": f"{relation_count:,}"},
                                  {"label": "关系验证通过率", "value": relation_accuracy},
                                  {"label": "匹配覆盖率", "value": f"{matched_relations}/{total_relations}"},
                              ]})

        # ── Phase 4: 策略输出 ─────────────────────────────
        yield {"type": "phase_progress", "phase": "strategy", "progress": 0.8}
        strategy_start = time.time()
        strategy_status = "pass"
        pk_checks = 0
        pk_passed = 0
        null_checks = 0
        null_passed = 0

        for obj in req.objects:
            if not obj.backing_asset_ids or not obj.primaryKey:
                continue

            aid = obj.backing_asset_ids[0]
            asset = asset_cache.get(aid) or self.asset_svc.get(aid)
            if not asset:
                continue

            for extra_id in obj.backing_asset_ids[1:]:
                try:
                    rule = next((rule for rule in obj.enrichment_bindings if rule.asset_id == extra_id), None)
                    enrichment_asset = asset_cache.get(extra_id) or self.asset_svc.get(extra_id)
                    if not rule or not rule.primary_source_column or not rule.enrichment_source_column:
                        raise ValueError("补充绑定待审核：请明确两侧物理关联列")
                    if not enrichment_asset:
                        raise ValueError("补充资产不可用")
                    from app.services.data_plane.entity_data_service import EntityDataService
                    from types import SimpleNamespace
                    data = EntityDataService(self.db)
                    binding = SimpleNamespace(filter_expr=None)
                    data._assert_unique_join_key(asset, binding, rule.primary_source_column, purpose="hydrate.enrichment.primary")
                    data._assert_unique_join_key(enrichment_asset, binding, rule.enrichment_source_column, purpose="hydrate.enrichment.secondary")
                    yield {"type":"phase_log", "phase":"strategy", "level":"OK", "msg":f"{obj.name}: {rule.primary_source_column} ← {extra_id}.{rule.enrichment_source_column} 一对一左关联键验证通过"}
                except Exception as exc:
                    strategy_status = "error"
                    yield {"type":"phase_log", "phase":"strategy", "level":"ERR", "msg":f"{obj.name} enrichment验证失败: {exc}"}
            pk_col = self._mapped_column(obj, obj.primaryKey)
            quote = self._quote(asset)
            quoted_pk = self._quoted(pk_col, quote)

            # PK 唯一性检查
            try:
                r = self.exec_svc.execute(ExecuteRequest(
                    asset_id=aid,
                    sql=f"SELECT {quoted_pk}, COUNT(*) AS cnt FROM <asset> GROUP BY {quoted_pk} HAVING COUNT(*) > 1 LIMIT 10",
                    params={}, purpose="hydrate.pk_check", bypass_cache=True,
                ))
                pk_checks += 1
                if not r.rows:
                    pk_passed += 1
                    yield {"type": "phase_log", "phase": "strategy", "level": "OK",
                           "msg": f"{obj.displayName or obj.name}.{pk_col}: 主键唯一 (0 重复)"}
                else:
                    strategy_status = "error"
                    yield {"type": "phase_log", "phase": "strategy", "level": "WARN",
                           "msg": f"{obj.displayName or obj.name}.{pk_col}: 发现 {len(r.rows)} 个重复主键"}
            except Exception as e:
                yield {"type": "phase_log", "phase": "strategy", "level": "ERR",
                       "msg": f"{obj.displayName or obj.name}.{pk_col}: PK 检查失败 - {e}"}
                strategy_status = "error"

            # 必填字段空值率检查
            for prop in obj.properties:
                if not prop.required and prop.name != obj.primaryKey:
                    continue
                null_checks += 1
                if prop.transform:
                    # The shared transform check above evaluates real source values,
                    # including None. Raw source nulls may intentionally be filled.
                    if f"{obj.name}.{prop.name}" in unmatched_props:
                        strategy_status = "error"
                    else:
                        null_passed += 1
                    continue
                column = prop.source_column or prop.source_field or prop.name
                property_asset = asset_cache.get(prop.source_asset_id) if prop.source_asset_id else asset
                quoted_column = self._quoted(column, self._quote(property_asset or asset))
                try:
                    r = self.exec_svc.execute(ExecuteRequest(
                        asset_id=prop.source_asset_id or aid,
                        sql=f"SELECT SUM(CASE WHEN {quoted_column} IS NULL THEN 1 ELSE 0 END) AS nn, COUNT(*) AS total FROM <asset>",
                        params={}, purpose="hydrate.null_check", bypass_cache=True,
                    ))
                    if r.rows:
                        nn = int(r.rows[0][0]) if r.rows[0][0] is not None else 0
                        total = int(r.rows[0][1]) if r.rows[0][1] is not None else 0
                        if total == 0:
                            raise ValueError("源表为空，无法验证必填字段")
                        ratio = nn / total
                        if nn == 0:
                            null_passed += 1
                            yield {"type": "phase_log", "phase": "strategy", "level": "OK",
                                   "msg": f"{obj.displayName or obj.name}.{prop.name}: 空值率 {ratio * 100:.1f}% (必填无空值)"}
                        else:
                            strategy_status = "error"
                            yield {"type": "phase_log", "phase": "strategy", "level": "WARN",
                                   "msg": f"{obj.displayName or obj.name}.{prop.name}: 空值率 {ratio * 100:.1f}% (必填字段存在空值)"}
                except Exception as e:
                    yield {"type": "phase_log", "phase": "strategy", "level": "ERR",
                           "msg": f"{obj.displayName or obj.name}.{prop.name}: 空值检查失败 - {e}"}
                    strategy_status = "error"

        strategy_elapsed = round(time.time() - strategy_start, 1)
        high_confidence = high_confidence_props
        manual_review = total_props - high_confidence_props
        yield {"type": "phase_progress", "phase": "strategy", "progress": 1.0}
        yield {
            "type": "phase_complete", "phase": "strategy", "status": strategy_status,
            "metrics": [
                {"label": "PK 唯一性", "value": f"{pk_passed}/{pk_checks}",
                 "tone": "pass" if pk_passed == pk_checks else "warn"},
                {"label": "必填非空率", "value": f"{null_passed}/{null_checks}",
                 "tone": "pass" if null_passed == null_checks else "warn"},
                {"label": "策略耗时", "value": f"{strategy_elapsed}s"},
            ],
        }
        phase_results.append({"key": "strategy", "label": "策略输出", "status": strategy_status,
                              "metrics": [
                                  {"label": "PK 唯一性", "value": f"{pk_passed}/{pk_checks}"},
                                  {"label": "必填非空率", "value": f"{null_passed}/{null_checks}"},
                                  {"label": "策略耗时", "value": f"{strategy_elapsed}s"},
                              ]})

        # ── 汇总 ─────────────────────────────────────────
        overall_status = "pass"
        if any(p["status"] == "error" for p in phase_results):
            overall_status = "error"
        elif any(p["status"] == "warn" for p in phase_results):
            overall_status = "warn"

        attribution_accuracy = f"{matched_props / total_props * 100:.1f}%" if total_props else "N/A"

        yield {
            "type": "drill_complete",
            "result": {
                "phases": phase_results,
                "logs": [],
                "selectedRows": total_rows,
                "selectedColumns": total_cols,
                "selectedSources": loaded_assets,
                "entityCount": sum(asset_rows.get(obj.backing_asset_ids[0], 0) for obj in req.objects if obj.backing_asset_ids),
                "relationCount": relation_count,
                "attributionAccuracy": attribution_accuracy,
                "highConfidenceAttribution": high_confidence,
                "manualReview": manual_review,
            },
            "status": overall_status,
        }

    @staticmethod
    def _mapped_column(obj: HydrateObject, name: str | None) -> str | None:
        prop = next((p for p in obj.properties if p.name == name), None)
        return (prop.source_column or prop.source_field or name) if prop else name

    def _quote(self, asset: Asset) -> str:
        from app.models.connection import Connection
        connection = self.db.get(Connection, asset.connection_id) if asset.connection_id else None
        return "`" if connection and connection.type in ("mysql", "hive", "clickhouse") else '"'

    @staticmethod
    def _quoted(name: str, quote: str) -> str:
        return quote + name.replace(quote, quote + quote) + quote

    def _table_quoted(self, name: str, quote: str) -> str:
        return ".".join(self._quoted(part, quote) for part in name.split("."))

    def _key_counts(self, asset: Asset, column: str) -> dict:
        # Keep the existing execution/audit/credential gate for both sources.
        # Masked keys cannot establish real equality, and must never be read
        # through an alternate unmasked channel to make the drill pass.
        if (asset.sensitivity_tags or {}).get(column):
            raise ValueError("敏感关联键不能用于跨连接水合，请使用受控的非敏感关联键")
        quoted = self._quoted(column, self._quote(asset))
        result = self.exec_svc.execute(ExecuteRequest(
            asset_id=asset.id, sql=f"SELECT {quoted}, COUNT(*) FROM <asset> WHERE {quoted} IS NOT NULL GROUP BY {quoted}",
            params={}, purpose="hydrate.cross_connection_keys", bypass_cache=True,
        ))
        # Grouped counts implement equality JOIN multiplicity without loading
        # all source instances or introducing write-side effects.
        if len(result.rows) > 100000:
            raise ValueError("关联键数量超过100000，请缩小资产范围后重新水合")
        return {row[0]: int(row[1]) for row in result.rows}
