"""MappingSuggestService — 半自动 ObjectType ↔ Asset 映射推荐。

策略：
1. 启发式（不依赖 LLM，离线零成本）
   - 列名规范化（snake/camel/lower、去标点、英文小写、中文不变）
   - 字符串相似度（token Jaccard + difflib ratio + 全等命中）
   - 类型相容性（string ↔ varchar/text；int ↔ bigint/int；date ↔ datetime/timestamp）
   - 列注释 token 与属性中文名的命中
2. LLM 兜底（启发式置信度 < 中等的属性聚合后送 LLM）
   - 输入：未匹中属性元数据 + 候选列池（含名/类型/注释/采样值）
   - 输出：JSON 数组 [{attribute_id, candidates: [{column, score, reason}]}]
   - 用项目 settings.LLM_BASE_URL/KEY/MODEL，OpenAI 兼容协议

返回格式（每属性 top 3）：
{
  attribute_id: "...",
  candidates: [
    {column: "user_id", score: 0.92, tier: "high", reason: "name_match", source: "heuristic"},
    {column: "uid",     score: 0.55, tier: "medium", reason: "fuzzy",      source: "heuristic"},
    ...
  ]
}
"""
from __future__ import annotations

import difflib
import json
import logging
import re

from sqlalchemy.orm import Session

from app.config import settings
from app.models.asset import Asset
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.object_binding import ObjectBinding

logger = logging.getLogger(__name__)


# 类型相容矩阵：左=本体属性 type，右=数据库列 type 关键词集合
TYPE_COMPAT: dict[str, set[str]] = {
    "string":   {"varchar", "char", "text", "string", "json", "longtext", "tinytext"},
    "text":     {"text", "varchar", "longtext", "tinytext", "string"},
    "int":      {"int", "bigint", "smallint", "tinyint", "integer", "mediumint"},
    "integer":  {"int", "bigint", "smallint", "tinyint", "integer", "mediumint"},
    "float":    {"float", "double", "real", "decimal", "numeric"},
    "decimal":  {"decimal", "numeric", "float", "double"},
    "boolean":  {"boolean", "bool", "tinyint", "bit"},
    "bool":     {"boolean", "bool", "tinyint", "bit"},
    "date":     {"date", "datetime", "timestamp"},
    "datetime": {"datetime", "timestamp", "date"},
    "timestamp":{"timestamp", "datetime", "date"},
    "json":     {"json", "text", "longtext"},
    "fk":       {"varchar", "char", "int", "bigint"},
    "enum":     {"varchar", "char", "enum", "text"},
}

# 中文 → 常见英文/拼音首字母（最小补丁；LLM 兜底解决长尾）
ZH_HINTS: dict[str, list[str]] = {
    "用户": ["user", "usr"],
    "客户": ["customer", "cust"],
    "手机": ["phone", "mobile", "tel"],
    "电话": ["phone", "tel"],
    "号码": ["number", "no", "num"],
    "身份证": ["id_card", "cert", "id_no"],
    "姓名": ["name", "username"],
    "时间": ["time", "ts", "date", "at"],
    "创建": ["create", "created"],
    "更新": ["update", "updated", "modify"],
    "状态": ["status", "state"],
    "类型": ["type", "kind"],
    "省份": ["province"],
    "城市": ["city"],
    "区县": ["district", "area"],
    "金额": ["amount", "fee", "money", "price"],
    "费用": ["fee", "amount", "cost"],
    "订单": ["order"],
    "工单": ["ticket", "order", "wo"],
    "携入": ["mnp_in", "port_in", "in"],
    "携出": ["mnp_out", "port_out", "out"],
    "渠道": ["channel"],
    "工程师": ["engineer"],
    "回访": ["callback", "feedback"],
    "投诉": ["complaint"],
}


def _normalize(s: str) -> str:
    """归一化列/属性名：保留中文，英文 lower 去下划线连字符空格。"""
    s = (s or "").strip()
    out = re.sub(r"[\s_\-\.]+", "", s)
    return out.lower()


def _tokens(s: str) -> set[str]:
    """按 snake_case / camelCase / 中文边界拆 token。"""
    s = (s or "").strip()
    if not s:
        return set()
    pieces = re.split(r"[\s_\-\.]+", s)
    out: set[str] = set()
    for p in pieces:
        # camelCase 拆分
        for sub in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+|[一-鿿]+", p):
            out.add(sub.lower())
        if p and p.lower() not in out:
            out.add(p.lower())
    return {t for t in out if t}


def _expand_zh(name: str) -> set[str]:
    """中文属性名扩展出英文/拼音候选 token（粗粒度）。"""
    out: set[str] = set()
    for zh, hints in ZH_HINTS.items():
        if zh in (name or ""):
            out.update(hints)
    return out


def _type_compat(attr_type: str, col_type: str) -> bool:
    if not attr_type or not col_type:
        return True  # 无信息时不否决
    a = attr_type.lower()
    c = col_type.lower()
    compat = TYPE_COMPAT.get(a, set())
    if not compat:
        return True  # 未知本体类型放过
    return any(k in c for k in compat)


def _heuristic_score(attr: EntityAttribute, col: dict) -> tuple[float, str]:
    """对单列打分。返回 (score 0~1, reason)。"""
    a_name = attr.name or ""
    a_type = attr.type or ""
    a_desc = attr.description or ""
    c_name = col.get("name") or ""
    c_type = col.get("type") or ""
    c_comment = col.get("comment") or ""

    score = 0.0
    reasons: list[str] = []

    # 完全等于（归一化后）
    if _normalize(a_name) == _normalize(c_name):
        score = max(score, 0.95)
        reasons.append("name=col")

    # token 重合
    a_tokens = _tokens(a_name) | _expand_zh(a_name)
    c_tokens = _tokens(c_name) | _tokens(c_comment)
    if a_tokens and c_tokens:
        inter = a_tokens & c_tokens
        if inter:
            jaccard = len(inter) / len(a_tokens | c_tokens)
            score = max(score, 0.4 + jaccard * 0.5)  # 0.4-0.9
            reasons.append(f"tokens={','.join(sorted(inter))[:40]}")

    # difflib 模糊匹配（仅英文）
    a_norm = _normalize(a_name)
    c_norm = _normalize(c_name)
    if a_norm and c_norm and re.match(r"^[a-z0-9]+$", c_norm):
        ratio = difflib.SequenceMatcher(None, a_norm, c_norm).ratio()
        if ratio >= 0.7:
            score = max(score, ratio * 0.85)
            reasons.append(f"fuzzy={ratio:.2f}")

    # 列注释 token 命中属性名
    if c_comment:
        a_text_tokens = _tokens(a_name) | _tokens(a_desc)
        c_comment_tokens = _tokens(c_comment)
        cc = a_text_tokens & c_comment_tokens
        if cc:
            score = max(score, 0.55)
            reasons.append(f"comment={','.join(sorted(cc))[:40]}")

    # 类型不容：直接惩罚
    if score > 0 and not _type_compat(a_type, c_type):
        score *= 0.5
        reasons.append(f"type_warn({a_type}↔{c_type})")

    # 主键提示：属性名带 id 的优先匹中 is_pk 列
    if "id" in a_tokens and col.get("is_pk"):
        score = max(score, 0.6)
        reasons.append("pk_hint")

    return score, ";".join(reasons) if reasons else ""


def _tier(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    if score > 0:
        return "low"
    return "none"


class MappingSuggestService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── 上层：扫所有 Asset 推荐给 ObjectType ───────────
    def suggest_assets(self, *, object_type_id: str) -> dict:
        """扫所有 table/sql_view Asset，按属性覆盖率排序推荐。

        返回：{
          object_type, total_attrs,
          existing_bindings: [{asset_id, role, field_count}],
          asset_suggestions: [{asset, coverage{high/medium/low/none/total},
                              top_attrs:[(attr_name,col,tier)], role_hint, already_bound_role}],
          combo: {primary: asset_id|null, enrichments: [asset_id, ...]}
        }
        """
        ot = self.db.get(OntologyEntity, object_type_id)
        if not ot:
            raise LookupError(f"ObjectType 不存在: {object_type_id}")
        attrs = list(ot.attributes)
        total = len(attrs)

        assets = (
            self.db.query(Asset)
            .filter(
                Asset.kind.in_(["table", "sql_view"]),
                Asset.status == "active",
            )
            .all()
        )

        existing = (
            self.db.query(ObjectBinding)
            .filter(ObjectBinding.object_type_id == object_type_id,
                    ObjectBinding.status == "active")
            .all()
        )
        bound_by_asset: dict[str, str] = {b.asset_id: b.role for b in existing}

        # 1. 对每个 Asset 跑启发式打分（仅 schema_snapshot 非空的）
        rows: list[dict] = []
        for asset in assets:
            schema = asset.schema_snapshot or []
            if not schema:
                continue
            attr_results: dict[str, tuple[float, str]] = {}  # attr_id -> (top_score, top_col)
            for attr in attrs:
                best_score = 0.0
                best_col = None
                for col in schema:
                    s, _r = _heuristic_score(attr, col)
                    if s > best_score:
                        best_score = s
                        best_col = col.get("name")
                if best_col:
                    attr_results[attr.id] = (best_score, best_col)

            cov = {"high": 0, "medium": 0, "low": 0, "none": 0, "total": total}
            top_attrs: list[dict] = []
            for attr in attrs:
                pair = attr_results.get(attr.id)
                if not pair:
                    cov["none"] += 1
                    continue
                score, col = pair
                tier = _tier(score)
                cov[tier] = cov.get(tier, 0) + 1
                if tier in ("high", "medium"):
                    top_attrs.append({
                        "attribute_name": attr.name,
                        "column": col,
                        "tier": tier,
                        "score": round(score, 3),
                    })
            top_attrs.sort(key=lambda x: x["score"], reverse=True)

            # 覆盖率排序权重：high*1.0 + medium*0.5
            rank_score = cov["high"] + cov["medium"] * 0.5

            rows.append({
                "asset": {
                    "id": asset.id,
                    "name": asset.alias or asset.name,
                    "kind": asset.kind,
                    "table": (asset.locator or {}).get("table") if asset.kind == "table" else None,
                    "domain": asset.domain,
                    "connection_id": asset.connection_id,
                },
                "coverage": cov,
                "rank_score": round(rank_score, 2),
                "top_attrs": top_attrs[:8],
                "already_bound_role": bound_by_asset.get(asset.id),
                # 内部用：每属性的最佳 (score,col)
                "_attr_best": {aid: {"score": s, "column": c}
                               for aid, (s, c) in attr_results.items()},
            })

        rows.sort(key=lambda r: r["rank_score"], reverse=True)

        # 2. 组合建议：top1 = primary；之后选互补 Asset 直至覆盖率达到 95% 或没有显著新增
        primary_id: str | None = None
        enrichments: list[str] = []
        covered_attrs: set[str] = set()  # 已被覆盖（high+medium）的属性 id

        if rows:
            head = rows[0]
            primary_id = head["asset"]["id"]
            for aid, info in head["_attr_best"].items():
                if _tier(info["score"]) in ("high", "medium"):
                    covered_attrs.add(aid)

            for r in rows[1:]:
                marginal = 0
                for aid, info in r["_attr_best"].items():
                    if aid in covered_attrs:
                        continue
                    if _tier(info["score"]) in ("high", "medium"):
                        marginal += 1
                if marginal >= max(2, total // 20):  # 至少能多带 ~5% 的属性才推荐
                    enrichments.append(r["asset"]["id"])
                    for aid, info in r["_attr_best"].items():
                        if _tier(info["score"]) in ("high", "medium"):
                            covered_attrs.add(aid)
                if len(covered_attrs) >= total * 0.95:
                    break

        # 清掉内部字段
        for r in rows:
            r.pop("_attr_best", None)

        return {
            "object_type": {"id": ot.id, "name": ot.name, "name_cn": ot.name_cn},
            "total_attrs": total,
            "existing_bindings": [
                {"binding_id": b.id, "asset_id": b.asset_id,
                 "role": b.role, "field_count": len(b.field_mappings or [])}
                for b in existing
            ],
            "asset_suggestions": rows,
            "combo": {
                "primary": primary_id,
                "enrichments": enrichments,
                "covered_attrs": len(covered_attrs),
            },
        }

    def suggest(self, *, object_type_id: str, asset_id: str,
                use_llm: bool = True, top_k: int = 3) -> dict:
        ot = self.db.get(OntologyEntity, object_type_id)
        if not ot:
            raise LookupError(f"ObjectType 不存在: {object_type_id}")
        asset = self.db.get(Asset, asset_id)
        if not asset:
            raise LookupError(f"Asset 不存在: {asset_id}")
        if asset.kind not in ("table", "sql_view"):
            raise ValueError(f"Asset kind={asset.kind} 不支持映射")
        schema = asset.schema_snapshot or []
        if not schema:
            raise ValueError("Asset 无 schema_snapshot，请先同步 schema")

        # 1. 启发式打分
        attrs = list(ot.attributes)
        results: list[dict] = []
        unmatched: list[EntityAttribute] = []
        for attr in attrs:
            scored: list[tuple[float, str, dict]] = []
            for col in schema:
                s, reason = _heuristic_score(attr, col)
                if s > 0:
                    scored.append((s, reason, col))
            scored.sort(key=lambda x: x[0], reverse=True)
            candidates = [
                {
                    "column": c["name"],
                    "column_type": c.get("type"),
                    "column_comment": c.get("comment"),
                    "is_pk": c.get("is_pk", False),
                    "score": round(s, 3),
                    "tier": _tier(s),
                    "reason": r,
                    "source": "heuristic",
                }
                for s, r, c in scored[:top_k]
            ]
            if not candidates or candidates[0]["tier"] in ("low", "none"):
                unmatched.append(attr)
            results.append({
                "attribute_id": attr.id,
                "attribute_name": attr.name,
                "attribute_type": attr.type,
                "attribute_description": attr.description,
                "candidates": candidates,
            })

        # 2. LLM 兜底
        if use_llm and unmatched:
            try:
                llm_results = self._llm_suggest(unmatched, schema, top_k)
                # 合并 LLM 候选
                idx = {r["attribute_id"]: r for r in results}
                for entry in llm_results:
                    aid = entry.get("attribute_id")
                    cur = idx.get(aid)
                    if not cur:
                        continue
                    existing_cols = {c["column"] for c in cur["candidates"]}
                    for cand in entry.get("candidates", []):
                        col_name = cand.get("column")
                        if not col_name or col_name in existing_cols:
                            continue
                        col_meta = next((c for c in schema if c.get("name") == col_name), {})
                        cur["candidates"].append({
                            "column": col_name,
                            "column_type": col_meta.get("type"),
                            "column_comment": col_meta.get("comment"),
                            "is_pk": col_meta.get("is_pk", False),
                            "score": float(cand.get("score", 0.7)),
                            "tier": _tier(float(cand.get("score", 0.7))),
                            "reason": cand.get("reason") or "llm",
                            "source": "llm",
                        })
                    cur["candidates"].sort(key=lambda x: x["score"], reverse=True)
                    cur["candidates"] = cur["candidates"][:top_k]
            except Exception as e:
                logger.warning("LLM 兜底失败（继续用启发式结果）: %s", e)

        # 3. 统计
        coverage = {"total": len(attrs), "high": 0, "medium": 0, "low": 0, "none": 0}
        for r in results:
            top_tier = r["candidates"][0]["tier"] if r["candidates"] else "none"
            coverage[top_tier] = coverage.get(top_tier, 0) + 1

        return {
            "object_type": {"id": ot.id, "name": ot.name, "name_cn": ot.name_cn},
            "asset": {
                "id": asset.id, "name": asset.alias or asset.name,
                "kind": asset.kind,
                "table": (asset.locator or {}).get("table") if asset.kind == "table" else None,
            },
            "coverage": coverage,
            "suggestions": results,
        }

    # ── 内部：LLM 兜底 ────────────────────────────────────
    def _llm_suggest(self, unmatched: list[EntityAttribute],
                     schema: list[dict], top_k: int) -> list[dict]:
        from app.services.copilot import get_llm_client
        if not settings.LLM_API_KEY:
            return []

        attrs_payload = [
            {
                "id": a.id, "name": a.name, "type": a.type,
                "description": a.description or "", "example": a.example or "",
            }
            for a in unmatched
        ]
        cols_payload = [
            {"name": c.get("name"), "type": c.get("type"),
             "comment": c.get("comment"), "is_pk": c.get("is_pk", False)}
            for c in schema
        ]

        prompt = f"""你是一个数据建模助手。下面给你一组本体属性 (attributes) 和一张数据表的列 (columns)。
为每个属性从列里挑出最匹配的至多 {top_k} 个候选列，按相关性从高到低。

判断依据（按重要性）：
1. 列名/列注释与属性中文名的语义对应（含中英文别名、拼音首字母、缩写）
2. 类型相容（string↔varchar、int↔bigint、date↔datetime 等）
3. 是否主键提示

只输出 JSON 数组，无任何解释/前后缀，不能用 markdown 代码块。每个元素：
{{"attribute_id": "...", "candidates": [{{"column": "...", "score": 0.0~1.0, "reason": "<20字简述>"}}]}}

如果某属性无任何合理候选，candidates 给空数组。

属性：{json.dumps(attrs_payload, ensure_ascii=False)}

列：{json.dumps(cols_payload, ensure_ascii=False)}
"""

        client = get_llm_client()
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=60,
        )
        content = resp.choices[0].message.content or "[]"
        # 容错：去掉 <think>...</think>（MiniMax 等推理模型）
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        # 去掉 markdown code fence
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
        # 提取第一个 [...] 数组（防止前后还有解释文本）
        m = re.search(r"\[.*\]", content, flags=re.DOTALL)
        if m:
            content = m.group(0)
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
        except Exception as e:
            logger.warning("LLM 输出解析失败: %s; raw=%s", e, content[:200])
        return []
