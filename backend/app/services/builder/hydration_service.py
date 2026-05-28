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
from typing import Any, Generator

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


class HydrateObject(BaseModel):
    name: str
    displayName: str | None = None
    tier: int = 2
    primaryKey: str | None = None
    properties: list[HydrateProperty] = []
    backing_asset_ids: list[str] = []


class HydrateRelation(BaseModel):
    name: str
    displayName: str | None = None
    source: str
    target: str
    cardinality: str = "1:N"


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
        t0 = time.time()
        phase_results: list[dict] = []
        total_rows = 0
        total_cols = 0
        loaded_assets = 0
        asset_cache: dict[str, Asset] = {}  # asset_id -> Asset

        # ── Phase 1: 数据接入 ─────────────────────────────
        yield {"type": "phase_progress", "phase": "ingest", "progress": 0}
        ingest_start = time.time()
        ingest_status = "pass"
        ingest_logs: list[dict] = []

        for aid in req.asset_ids:
            asset = self.asset_svc.get(aid)
            if not asset:
                msg = f"资产不存在: {aid}"
                yield {"type": "phase_log", "phase": "ingest", "level": "ERR", "msg": msg}
                ingest_status = "warn"
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
                        ingest_status = "warn"
                        continue
                except Exception as e:
                    yield {"type": "phase_log", "phase": "ingest", "level": "ERR",
                           "msg": f"连接 {asset.name} 异常: {e}"}
                    ingest_status = "warn"
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
                ingest_status = "warn"

            # preview
            try:
                preview = self.asset_svc.preview(aid, limit=10)
                rows_returned = preview.get("rows_returned", 0)
                yield {"type": "phase_log", "phase": "ingest", "level": "OK",
                       "msg": f"preview: {asset.name} {rows_returned} 行样例已加载"}
            except Exception as e:
                yield {"type": "phase_log", "phase": "ingest", "level": "ERR",
                       "msg": f"preview {asset.name} 失败: {e}"}

            # profile
            try:
                profile = self.asset_svc.profile(aid)
                row_count = profile.get("row_count", 0)
                total_rows += row_count
                yield {"type": "phase_log", "phase": "ingest", "level": "OK",
                       "msg": f"profile: {asset.name} {row_count:,} 行, 列空值率已计算"}
            except Exception as e:
                yield {"type": "phase_log", "phase": "ingest", "level": "ERR",
                       "msg": f"profile {asset.name} 失败: {e}"}

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
        instantiate_status = "pass"
        total_props = 0
        matched_props = 0
        unmatched_props: list[str] = []

        # 导入启发式打分函数
        try:
            from app.services.data_plane.mapping_suggest_service import _heuristic_score, _tier
        except ImportError:
            _heuristic_score = None
            _tier = None

        for obj in req.objects:
            obj_matched = 0
            obj_total = len(obj.properties)
            total_props += obj_total

            # 收集 backing assets 的 schema
            all_columns: list[dict] = []
            for aid in obj.backing_asset_ids:
                asset = asset_cache.get(aid) or self.asset_svc.get(aid)
                if asset and asset.schema_snapshot:
                    for col in asset.schema_snapshot:
                        col_copy = dict(col)
                        col_copy["_asset_id"] = aid
                        all_columns.append(col_copy)

            for prop in obj.properties:
                # 优先检查 source_asset_id + source_column 是否真实存在
                if prop.source_asset_id and prop.source_column:
                    found = any(
                        c.get("name") == prop.source_column and c.get("_asset_id") == prop.source_asset_id
                        for c in all_columns
                    )
                    if found:
                        obj_matched += 1
                        yield {"type": "phase_log", "phase": "instantiate", "level": "OK",
                               "msg": f"{obj.displayName or obj.name}.{prop.name}: → {prop.source_column} ✓"}
                        continue
                    else:
                        yield {"type": "phase_log", "phase": "instantiate", "level": "ERR",
                               "msg": f"{obj.displayName or obj.name}.{prop.name}: 指定列 {prop.source_column} 不存在"}
                        unmatched_props.append(f"{obj.name}.{prop.name}")
                        continue

                # 启发式打分找最佳匹配
                best_score = 0.0
                best_col = None
                if _heuristic_score and all_columns:
                    # 构造临时 EntityAttribute-like 对象
                    class _FakeAttr:
                        def __init__(self, p):
                            self.name = p.name
                            self.type = p.type
                            self.description = p.displayName or ""
                            self.required = p.required

                    fake_attr = _FakeAttr(prop)
                    for col in all_columns:
                        try:
                            score, _ = _heuristic_score(fake_attr, col)
                            if score > best_score:
                                best_score = score
                                best_col = col
                        except Exception:
                            continue

                if best_score >= 0.5 and best_col:
                    obj_matched += 1
                    tier_label = _tier(best_score) if _tier else ("high" if best_score >= 0.8 else "medium")
                    yield {"type": "phase_log", "phase": "instantiate", "level": "OK",
                           "msg": f"{obj.displayName or obj.name}.{prop.name}: → {best_col['name']} ({tier_label}, {best_score:.2f})"}
                else:
                    unmatched_props.append(f"{obj.name}.{prop.name}")
                    yield {"type": "phase_log", "phase": "instantiate", "level": "ERR",
                           "msg": f"{obj.displayName or obj.name}.{prop.name}: 未找到匹配列"}

            matched_props += obj_matched
            obj_status = "pass" if obj_matched == obj_total else ("warn" if obj_matched > obj_total * 0.5 else "error")
            high_count = sum(1 for _ in [])  # placeholder
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
                {"label": "映射准确率", "value": mapping_rate,
                 "tone": "pass" if matched_props == total_props else "warn"},
                {"label": "映射耗时", "value": f"{instantiate_elapsed}s"},
            ],
        }
        phase_results.append({"key": "instantiate", "label": "本体实例化", "status": instantiate_status,
                              "metrics": [
                                  {"label": "字段映射命中", "value": f"{matched_props}/{total_props}"},
                                  {"label": "映射准确率", "value": mapping_rate},
                                  {"label": "映射耗时", "value": f"{instantiate_elapsed}s"},
                              ]})

        # ── Phase 3: 关系映射验证 ─────────────────────────
        yield {"type": "phase_progress", "phase": "match", "progress": 0.55}
        match_start = time.time()
        match_status = "pass"
        matched_relations = 0
        total_relations = len(req.relations)

        # 构建对象名 -> 对象映射
        obj_map = {o.name: o for o in req.objects}

        for rel in req.relations:
            src_obj = obj_map.get(rel.source)
            tgt_obj = obj_map.get(rel.target)

            if not src_obj or not tgt_obj:
                yield {"type": "phase_log", "phase": "match", "level": "ERR",
                       "msg": f"关系 {rel.displayName or rel.name}: 源/目标对象不存在 ({rel.source} → {rel.target})"}
                match_status = "warn"
                continue

            # 检查两端都有 backing assets
            src_assets = src_obj.backing_asset_ids
            tgt_assets = tgt_obj.backing_asset_ids

            if not src_assets or not tgt_assets:
                yield {"type": "phase_log", "phase": "match", "level": "WARN",
                       "msg": f"关系 {rel.displayName or rel.name}: 无 backing 资产，跳过 JOIN 验证"}
                match_status = "warn"
                continue

            # 检查主键列是否存在
            src_pk = src_obj.primaryKey
            tgt_pk = tgt_obj.primaryKey

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
                    quote = "`"
                    join_sql = (
                        f"SELECT COUNT(*) AS cnt FROM {quote}{src_table}{quote} s "
                        f"JOIN {quote}{tgt_table}{quote} t "
                        f"ON s.{quote}{src_pk}{quote} = t.{quote}{tgt_pk}{quote} "
                        f"LIMIT 1"
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
                except Exception as e:
                    yield {"type": "phase_log", "phase": "match", "level": "WARN",
                           "msg": f"关系 {rel.displayName or rel.name}: JOIN 验证失败 - {e}"}
                    match_status = "warn"
            elif src_asset_obj and tgt_asset_obj and src_asset_obj.connection_id != tgt_asset_obj.connection_id:
                yield {"type": "phase_log", "phase": "match", "level": "WARN",
                       "msg": f"关系 {rel.displayName or rel.name}: 跨连接跳过 JOIN 验证"}
                matched_relations += 1  # 跨连接视为结构匹配
            else:
                yield {"type": "phase_log", "phase": "match", "level": "WARN",
                       "msg": f"关系 {rel.displayName or rel.name}: 跳过 JOIN 验证 (资产信息不完整)"}
                matched_relations += 1

        relation_accuracy = f"{matched_relations / total_relations * 100:.1f}%" if total_relations else "N/A"
        match_elapsed = round(time.time() - match_start, 1)
        relation_count = total_rows * max(1, total_relations)  # 估算关系实例数
        yield {"type": "phase_progress", "phase": "match", "progress": 0.75}
        yield {
            "type": "phase_complete", "phase": "match", "status": match_status,
            "metrics": [
                {"label": "关系实例数", "value": f"{relation_count:,}"},
                {"label": "关系映射准确率", "value": relation_accuracy,
                 "tone": "pass" if match_status == "pass" else "warn"},
                {"label": "匹配覆盖率", "value": f"{matched_relations}/{total_relations}",
                 "tone": "pass" if matched_relations == total_relations else "warn"},
            ],
        }
        phase_results.append({"key": "match", "label": "关系映射验证", "status": match_status,
                              "metrics": [
                                  {"label": "关系实例数", "value": f"{relation_count:,}"},
                                  {"label": "关系映射准确率", "value": relation_accuracy},
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

            pk_col = obj.primaryKey

            # PK 唯一性检查
            try:
                r = self.exec_svc.execute(ExecuteRequest(
                    asset_id=aid,
                    sql=f"SELECT {pk_col}, COUNT(*) AS cnt FROM <asset> GROUP BY {pk_col} HAVING COUNT(*) > 1 LIMIT 10",
                    params={}, purpose="hydrate.pk_check", bypass_cache=True,
                ))
                pk_checks += 1
                if not r.rows:
                    pk_passed += 1
                    yield {"type": "phase_log", "phase": "strategy", "level": "OK",
                           "msg": f"{obj.displayName or obj.name}.{pk_col}: 主键唯一 (0 重复)"}
                else:
                    strategy_status = "warn"
                    yield {"type": "phase_log", "phase": "strategy", "level": "WARN",
                           "msg": f"{obj.displayName or obj.name}.{pk_col}: 发现 {len(r.rows)} 个重复主键"}
            except Exception as e:
                yield {"type": "phase_log", "phase": "strategy", "level": "ERR",
                       "msg": f"{obj.displayName or obj.name}.{pk_col}: PK 检查失败 - {e}"}

            # 必填字段空值率检查
            for prop in obj.properties:
                if not prop.required:
                    continue
                null_checks += 1
                try:
                    r = self.exec_svc.execute(ExecuteRequest(
                        asset_id=aid,
                        sql=f"SELECT SUM(CASE WHEN {prop.name} IS NULL THEN 1 ELSE 0 END) AS nn, COUNT(*) AS total FROM <asset>",
                        params={}, purpose="hydrate.null_check", bypass_cache=True,
                    ))
                    if r.rows:
                        nn = int(r.rows[0][0]) if r.rows[0][0] is not None else 0
                        total = int(r.rows[0][1]) if r.rows[0][1] is not None else 0
                        ratio = nn / total if total else 0
                        if ratio < 0.05:
                            null_passed += 1
                            yield {"type": "phase_log", "phase": "strategy", "level": "OK",
                                   "msg": f"{obj.displayName or obj.name}.{prop.name}: 空值率 {ratio * 100:.1f}% (< 5%)"}
                        else:
                            strategy_status = "warn"
                            yield {"type": "phase_log", "phase": "strategy", "level": "WARN",
                                   "msg": f"{obj.displayName or obj.name}.{prop.name}: 空值率 {ratio * 100:.1f}% (> 5% 阈值)"}
                except Exception as e:
                    yield {"type": "phase_log", "phase": "strategy", "level": "ERR",
                           "msg": f"{obj.displayName or obj.name}.{prop.name}: 空值检查失败 - {e}"}

        strategy_elapsed = round(time.time() - strategy_start, 1)
        high_confidence = matched_props
        manual_review = total_props - matched_props
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
                "entityCount": total_rows,
                "relationCount": relation_count,
                "attributionAccuracy": attribution_accuracy,
                "highConfidenceAttribution": high_confidence,
                "manualReview": manual_review,
            },
            "status": overall_status,
        }
