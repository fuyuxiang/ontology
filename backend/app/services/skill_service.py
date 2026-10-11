"""Instruction skill lifecycle, authorization and immutable dependency snapshots."""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable

from fastapi import HTTPException
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.action import EntityAction
from app.models.agent import Agent
from app.models.asset import Asset
from app.models.entity import OntologyEntity
from app.models.function import OntologyFunction
from app.models.object_binding import ObjectBinding
from app.models.scenario import ScenarioDict
from app.models.skill import Skill
from app.models.skill_tool import SkillTool
from app.models.skill_version import SkillTestRun, SkillVersion
from app.models.user import User
from app.models.version import OntologyVersion, OntologyVersionEntity
from app.models.version_components import OntologyVersionAction, OntologyVersionFunction

META_DEFAULTS = {
    "ontology_id": None, "ontology_version_id": None, "entity_ids": [],
    "applicable_tasks": "", "excluded_tasks": "", "owner_team": "",
    "visibility": "private", "tags": [],
}
CONTENT_FIELDS = (
    "name", "description", "prompt_template", "input_schema", "output_schema",
    "tools", "test_cases", "asset_refs",
)
TestRunner = Callable[[dict, dict, User], dict]


def _fingerprint(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), default=str).encode()).hexdigest()


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _iso(value):
    from app.utils.time import utc_iso
    return utc_iso(value)


class SkillService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def can_edit(skill: Skill, user: User) -> bool:
        return bool(user and user.is_active and user.role in {"admin", "editor"} and
                    (user.role == "admin" or skill.created_by == user.id))

    @classmethod
    def can_read(cls, skill: Skill, user: User) -> bool:
        return bool(user and user.is_active and
                    (user.role == "admin" or skill.created_by == user.id or
                     (skill.config_json or {}).get("visibility") == "workspace"))

    def get(self, skill_id: str, user: User, edit: bool = False) -> Skill:
        skill = self.db.get(Skill, skill_id)
        # A private skill must not expose its existence to other users.
        if not skill or not self.can_read(skill, user):
            raise HTTPException(404, "技能不存在或无权访问")
        if edit and not self.can_edit(skill, user):
            raise HTTPException(403, "仅技能创建者或管理员可以修改")
        return skill

    def list(self, user: User, ontology_id=None, status=None, search=None) -> list[dict]:
        skills = self.db.query(Skill).order_by(Skill.updated_at.desc()).all()
        return [self.to_dict(s, user) for s in skills if self.can_read(s, user)
                and (not ontology_id or ontology_id in self.referenced_ontology_ids(s))
                and (not status or s.status == status)
                and (not search or search.lower() in f"{s.name} {s.description}".lower())]

    def create(self, data: dict, user: User) -> dict:
        if not user.is_active or user.role not in {"admin", "editor"}:
            raise HTTPException(403, "需要管理员或编辑者权限")
        config = copy.deepcopy(META_DEFAULTS)
        config.update({k: copy.deepcopy(data[k]) for k in META_DEFAULTS if k in data})
        skill = Skill(**{k: copy.deepcopy(data[k]) for k in CONTENT_FIELDS if k in data},
                      config_json=config, skill_type="instruction", status="draft",
                      current_version=0, created_by=user.id)
        self.db.add(skill)
        self.db.flush()
        self._check_draft_dependencies(skill)
        self.db.commit()
        self.db.refresh(skill)
        return self.to_dict(skill, user)

    def update(self, skill: Skill, data: dict, user: User) -> dict:
        if skill.status == "archived":
            raise HTTPException(409, "请先恢复已归档技能再编辑")
        config = copy.deepcopy(skill.config_json or {})
        for key, value in data.items():
            if key in META_DEFAULTS:
                config[key] = copy.deepcopy(value if value is not None else META_DEFAULTS[key])
            elif key in CONTENT_FIELDS:
                if value is None:
                    raise HTTPException(422, f"{key} 不能为 null")
                setattr(skill, key, copy.deepcopy(value))
        skill.config_json = config
        self._check_draft_dependencies(skill)
        self.db.commit()
        self.db.refresh(skill)
        return self.to_dict(skill, user)

    def content(self, skill: Skill) -> dict:
        data = {"id": skill.id, "skill_id": skill.id}
        for field in CONTENT_FIELDS:
            value = getattr(skill, field)
            if field in ("tools", "test_cases", "asset_refs"):
                value = _list(value)
            elif field in ("input_schema", "output_schema"):
                value = value if isinstance(value, dict) else {}
            else:
                value = value or ""
            data[field] = copy.deepcopy(value)
        config = skill.config_json or {}
        data.update({k: copy.deepcopy(config.get(k, v)) for k, v in META_DEFAULTS.items()})
        return data

    def versions(self, skill: Skill) -> list[dict]:
        return [self.version_dict(v) for v in self.db.query(SkillVersion).filter_by(
            skill_id=skill.id).order_by(SkillVersion.version.desc()).all()]

    def referenced_ontology_ids(self, skill: Skill) -> list[str]:
        ids = {(skill.config_json or {}).get("ontology_id")}
        ids.update(snapshot.get("ontology_id") for (snapshot,) in self.db.query(
            SkillVersion.snapshot_json).filter_by(skill_id=skill.id).all())
        return sorted(value for value in ids if value)

    @staticmethod
    def version_dict(version: SkillVersion, include_snapshot=False) -> dict:
        data = {"id": version.id, "skill_id": version.skill_id, "version": version.version,
                "description": version.description, "fingerprint": version.fingerprint,
                "created_by": version.created_by, "created_at": _iso(version.created_at)}
        if include_snapshot:
            from app.api.v1.models import _redact_config
            data["snapshot_json"] = _redact_config(copy.deepcopy(version.snapshot_json))
        return data

    def version(self, skill: Skill, number: int) -> SkillVersion:
        version = self.db.query(SkillVersion).filter_by(skill_id=skill.id, version=number).first()
        if not version:
            raise HTTPException(404, "技能版本不存在")
        return version

    def get_published_snapshot(self, skill_id: str, version: int, user: User,
                               allow_archived: bool = False) -> dict:
        skill = self.get(skill_id, user)
        if skill.status == "archived" and not allow_archived:
            raise HTTPException(409, "已归档技能不能新挂载")
        if not skill.current_version:
            raise HTTPException(409, "技能尚未发布")
        return copy.deepcopy(self.version(skill, version).snapshot_json)

    def to_dict(self, skill: Skill, user: User) -> dict:
        data = self.content(skill)
        versions = self.versions(skill)
        validation = self.validate(skill, user)
        latest = versions[0] if versions else None
        data.update({"status": skill.status, "current_version": skill.current_version,
                     "referenced_ontology_ids": self.referenced_ontology_ids(skill),
                     "has_changes": not latest or latest["fingerprint"] != validation["fingerprint"],
                     "versions": versions, "ref_count": len({r["agent_id"] for r in self.references(skill)}),
                     "can_edit": self.can_edit(skill, user), "created_by": skill.created_by,
                     "created_at": _iso(skill.created_at), "updated_at": _iso(skill.updated_at)})
        return data

    def _asset_allowed(self, asset: Asset, ontology: ScenarioDict | None,
                       entity_ids: set[str]) -> bool:
        if asset.status != "active":
            return False
        domain_matches = not asset.domain or (ontology and asset.domain in
                                              {ontology.id, ontology.code, ontology.name})
        if not domain_matches:
            return False
        if asset.kind == "document":
            return True
        return bool(entity_ids and self.db.query(ObjectBinding).filter(
            ObjectBinding.asset_id == asset.id, ObjectBinding.object_type_id.in_(entity_ids),
            ObjectBinding.status == "active").first())

    def _dependencies(self, skill: Skill) -> tuple[dict, list[str]]:
        content = self.content(skill)
        errors: list[str] = []
        ontology_id, version_id = content["ontology_id"], content["ontology_version_id"]
        ontology = self.db.get(ScenarioDict, ontology_id) if ontology_id else None
        version = self.db.get(OntologyVersion, version_id) if version_id else None
        deps = {"ontology_version": None, "entities": [], "functions": [], "actions": [], "assets": []}
        if ontology_id and not ontology:
            errors.append("关联本体不存在")
        if version_id and not version:
            errors.append("关联本体版本不存在")
        elif version:
            if version.ontology_id != ontology_id:
                errors.append("本体版本不属于关联本体")
            if version.status != "published":
                errors.append("依赖本体版本必须已发布")
            deps["ontology_version"] = {"id": version.id, "ontology_id": version.ontology_id,
                                         "version_number": version.version_number, "name": version.name}
        snapshots = self.db.query(OntologyVersionEntity).filter_by(version_id=version_id).all() if version else []
        entity_map = {e.source_entity_id: e for e in snapshots}
        selected = set(content["entity_ids"])
        for entity_id in content["entity_ids"]:
            entity = self.db.get(OntologyEntity, entity_id)
            if not entity or entity.ontology_id != ontology_id:
                errors.append(f"对象 {entity_id} 不属于关联本体或已删除")
                continue
            snap = entity_map.get(entity_id)
            if version and not snap:
                errors.append(f"对象 {entity.name} 不在选定本体版本内")
                continue
            deps["entities"].append({"id": entity.id, "name": snap.name if snap else entity.name,
                "name_cn": snap.name_cn if snap else entity.name_cn,
                "ontology_id": ontology_id, "version_entity_id": snap.id if snap else None,
                "description": (snap.description if snap else entity.description) or "",
                "publish_config": copy.deepcopy((snap.publish_config if snap else entity.publish_config) or {}),
                "attributes": [{"id": a.source_attribute_id, "name": a.name, "type": a.type,
                                "source_table": a.source_table, "source_field": a.source_field}
                               for a in snap.attributes] if snap else []})
        for ref in content["tools"]:
            ref_type, ref_id = ref.get("type"), ref.get("id")
            if ref_type not in {"function", "action"} or not ref_id:
                errors.append("能力引用必须包含 function/action 类型和 id")
                continue
            model = OntologyFunction if ref_type == "function" else EntityAction
            snap_model = OntologyVersionFunction if ref_type == "function" else OntologyVersionAction
            source_field = snap_model.source_function_id if ref_type == "function" else snap_model.source_action_id
            tool = self.db.get(model, ref_id)
            if not tool:
                errors.append(f"{ref_type} {ref_id} 不存在")
                continue
            snap = self.db.query(snap_model).filter(snap_model.version_id == version_id,
                                                       source_field == ref_id).first() if version else None
            tool_entities = set(_list(getattr(tool, "entity_ids", None))) | ({tool.entity_id} if tool.entity_id else set())
            if tool.ontology_id and tool.ontology_id != ontology_id:
                errors.append(f"能力 {tool.name} 不属于关联本体")
                continue
            global_action = (ref_type == "action" and tool.category == "system"
                             and not tool_entities and snap is not None)
            if not global_action and (not tool_entities or not tool_entities.issubset(selected)):
                errors.append(f"能力 {tool.name} 的对象依赖不在技能对象范围内")
                continue
            if version and not snap:
                errors.append(f"能力 {tool.name} 不在选定本体版本内")
                continue
            if not version and tool.status != "active":
                errors.append(f"能力 {tool.name} 未启用")
                continue
            source = snap or tool
            fields = ("name", "description", "input_schema", "return_type", "logic_type", "logic_body", "callable_name") if ref_type == "function" else (
                "name", "description", "parameters_json", "output_schema", "action_type", "type_config", "category")
            payload = {key: copy.deepcopy(getattr(source, key, None)) for key in fields}
            payload.update({"id": ref_id, "type": ref_type, "ontology_id": ontology_id,
                            "entity_id": tool.entity_id, "entity_ids": sorted(tool_entities),
                            "snapshot_id": snap.id if snap else None})
            deps["functions" if ref_type == "function" else "actions"].append(payload)
        for asset_id in content["asset_refs"]:
            asset = self.db.get(Asset, asset_id)
            if not asset or not self._asset_allowed(asset, ontology, selected):
                errors.append(f"参考资产 {asset_id} 不可用或不在本体范围内")
                continue
            deps["assets"].append({"id": asset.id, "name": asset.name, "kind": asset.kind,
                                   "description": asset.description or "", "domain": asset.domain,
                                   "parsed_summary": asset.parsed_summary or ""})
        return deps, errors

    def _check_draft_dependencies(self, skill: Skill):
        _, errors = self._dependencies(skill)
        if errors:
            self.db.rollback()
            raise HTTPException(422, {"message": "技能依赖无效", "errors": errors})

    @staticmethod
    def _schema_errors(schema: dict, path: str, depth=0) -> list[str]:
        errors = []
        if depth > 10:
            return [f"{path} 层级过深"]
        if "type" in schema and schema["type"] not in ("object", "array", "string", "number", "integer", "boolean", "null"):
            errors.append(f"{path}.type 必须是有效 JSON Schema 类型")
        if "required" in schema and (not isinstance(schema["required"], list) or
                                      any(not isinstance(v, str) for v in schema["required"])):
            errors.append(f"{path}.required 必须是字段名称数组")
        if "properties" in schema:
            if not isinstance(schema["properties"], dict):
                errors.append(f"{path}.properties 必须是对象")
            else:
                for key, value in schema["properties"].items():
                    errors += SkillService._schema_errors(value, f"{path}.{key}", depth+1) if isinstance(value, dict) else [f"{path}.{key} 必须是 schema 对象"]
        if "items" in schema:
            errors += SkillService._schema_errors(schema["items"], f"{path}.items", depth+1) if isinstance(schema["items"], dict) else [f"{path}.items 必须是 schema 对象"]
        return errors

    def validate(self, skill: Skill, user: User) -> dict:
        content = self.content(skill)
        dependencies, errors = self._dependencies(skill)
        if not content["name"].strip():
            errors.append("技能名称不能为空")
        if not content["prompt_template"].strip():
            errors.append("请填写业务操作指引")
        if not content["ontology_id"]:
            errors.append("请选择关联本体")
        if not content["ontology_version_id"]:
            errors.append("请选择已发布的本体版本")
        if not content["entity_ids"]:
            errors.append("请选择技能适用的对象范围")
        if not content["test_cases"]:
            errors.append("请至少添加一个有预期结果的测试用例")
        case_ids = [c.get("id") for c in content["test_cases"]]
        if len(set(case_ids)) != len(case_ids):
            errors.append("测试用例 id 不能重复")
        for case in content["test_cases"]:
            if not case.get("input"):
                errors.append(f"测试 {case.get('name', '')} 的输入不能为空")
            expectations = _list(case.get("expected_keywords")) + _list(case.get("expected_tools"))
            if not expectations or any(not isinstance(e, str) or not e.strip() for e in expectations):
                errors.append(f"测试 {case.get('name', '')} 需要非空的预期关键词或工具")
        for field in ("input_schema", "output_schema"):
            errors += self._schema_errors(content[field], field)
        snapshot = {**content, "dependencies": dependencies}
        return {"valid": not errors, "errors": errors, "warnings": [],
                "fingerprint": _fingerprint(snapshot), "dependencies": dependencies}

    def snapshot(self, skill: Skill, user: User) -> dict:
        result = self.validate(skill, user)
        return {**self.content(skill), "dependencies": result["dependencies"],
                "fingerprint": result["fingerprint"]}

    @staticmethod
    def test_run_dict(run: SkillTestRun) -> dict:
        return {"id": run.id, "skill_id": run.skill_id, "fingerprint": run.fingerprint,
                "validation_level": run.validation_level, "status": run.status, "passed": run.passed,
                "case_results": run.case_results, "errors": run.errors,
                "created_by": run.created_by, "created_at": _iso(run.created_at)}

    def test_runs(self, skill: Skill) -> list[dict]:
        return [self.test_run_dict(run) for run in self.db.query(SkillTestRun).filter_by(
            skill_id=skill.id).order_by(SkillTestRun.created_at.desc()).limit(100).all()]

    def run_tests(self, skill: Skill, user: User, runner: TestRunner | None = None,
                  test_case_ids: list[str] | None = None) -> dict:
        validation = self.validate(skill, user)
        snapshot = {**self.content(skill), "dependencies": validation["dependencies"],
                    "fingerprint": validation["fingerprint"]}
        cases = snapshot["test_cases"]
        if test_case_ids is not None:
            unknown = set(test_case_ids) - {c["id"] for c in cases}
            if unknown or not test_case_ids:
                raise HTTPException(422, "请选择存在的测试用例")
            cases = [c for c in cases if c["id"] in test_case_ids]
        errors = list(validation["errors"])
        results = []
        if validation["valid"] and runner:
            for case in cases:
                case_errors: list[str] = []
                try:
                    output = runner(copy.deepcopy(snapshot), copy.deepcopy(case), user)
                    if not isinstance(output, dict):
                        raise ValueError("测试执行器未返回有效结果")
                    answer = str(output.get("answer") or "")
                    tool_runs = _list(output.get("tool_runs"))
                    if output.get("error"):
                        case_errors.append(str(output["error"]))
                    if not answer.strip():
                        case_errors.append("执行未产生有效回答")
                    for keyword in case.get("expected_keywords", []):
                        if keyword.casefold() not in answer.casefold():
                            case_errors.append(f"回答缺少预期关键词：{keyword}")
                    executed = self._executed_tools(tool_runs, snapshot)
                    for tool in case.get("expected_tools", []):
                        if tool not in executed:
                            case_errors.append(f"未成功调用预期工具：{tool}")
                except Exception as exc:
                    answer, tool_runs = "", []
                    case_errors.append(f"运行失败：{exc}")
                results.append({"id": case["id"], "name": case["name"], "passed": not case_errors,
                                "answer": answer, "tool_runs": tool_runs, "errors": case_errors})
        elif validation["valid"]:
            errors.append("未配置真实测试执行器；仅完成静态依赖校验，没有验证技能行为")
        passed = bool(runner and validation["valid"] and results and all(r["passed"] for r in results))
        run = SkillTestRun(skill_id=skill.id, fingerprint=validation["fingerprint"],
                           validation_level="runtime" if runner and validation["valid"] else "static",
                           status="passed" if passed else "failed",
                           passed=passed, case_results=results, errors=errors, created_by=user.id)
        # A static result cannot be used as runtime publication evidence.
        if not runner and validation["valid"]:
            run.status = "not_run"
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return self.test_run_dict(run)

    @staticmethod
    def _executed_tools(runs: list[dict], snapshot: dict) -> set[str]:
        executed = set()
        deps = snapshot["dependencies"]
        for run in runs:
            if not isinstance(run, dict) or run.get("success") is False or run.get("status") in {"error", "failed"}:
                continue
            result = run.get("result")
            if isinstance(result, dict) and (result.get("error") or result.get("success") is False):
                continue
            args = run.get("arguments") or run.get("args") or {}
            names = {str(run.get(k)) for k in ("tool", "name", "tool_name") if run.get(k)}
            if isinstance(args, dict):
                names |= {str(args[k]) for k in ("callable_name", "function_id", "action_id", "action_name") if args.get(k)}
            executed |= names
            for dependency in deps["functions"] + deps["actions"]:
                aliases = {str(dependency[k]) for k in ("id", "name", "callable_name") if dependency.get(k)}
                if aliases & names:
                    executed |= aliases
        return executed

    def publish(self, skill: Skill, user: User, description: str = "") -> dict:
        if skill.status == "archived":
            raise HTTPException(409, "已归档技能不能发布")
        validation = self.validate(skill, user)
        if not validation["valid"]:
            raise HTTPException(422, {"message": "发布检查未通过", "errors": validation["errors"]})
        cases = {case["id"] for case in self.content(skill)["test_cases"]}
        runs = self.db.query(SkillTestRun).filter_by(skill_id=skill.id,
            fingerprint=validation["fingerprint"], validation_level="runtime", passed=True).all()
        tested = {r["id"] for run in runs for r in run.case_results if r.get("passed")}
        if not cases.issubset(tested):
            raise HTTPException(409, "请先完成当前草稿及依赖指纹的全部真实测试")
        latest = self.db.query(SkillVersion).filter_by(skill_id=skill.id).order_by(SkillVersion.version.desc()).first()
        if latest and latest.fingerprint == validation["fingerprint"]:
            raise HTTPException(409, "当前内容已发布，没有需要发布的新变更")
        number = (latest.version if latest else 0) + 1
        snapshot = {**self.content(skill), "dependencies": validation["dependencies"],
                    "fingerprint": validation["fingerprint"], "version": number}
        version = SkillVersion(skill_id=skill.id, version=number, snapshot_json=snapshot,
            description=description, fingerprint=validation["fingerprint"], created_by=user.id)
        self.db.add(version)
        skill.current_version, skill.status = number, "active"
        skill.reviewed_by = user.id
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(409, "技能已被其他会话发布，请刷新后重试") from exc
        return self.to_dict(skill, user)

    def archive(self, skill: Skill, user: User, restore=False) -> dict:
        skill.status = ("active" if skill.current_version else "draft") if restore else "archived"
        self.db.commit()
        return self.to_dict(skill, user)

    def references(self, skill: Skill) -> list[dict]:
        refs: list[dict] = []
        agents = {a.id: a for a in self.db.query(Agent).all()}
        for agent in agents.values():
            for binding in _list((agent.tools_config or {}).get("skill_bindings")):
                if isinstance(binding, dict) and binding.get("skill_id") == skill.id:
                    refs.append({"agent_id": agent.id, "agent_name": agent.name,
                                 "version": binding.get("version"), "status": agent.status, "source": "draft"})
        # AgentVersion belongs to the Agent runtime integration; lazily load it so
        # skill CRUD remains usable independently during schema migration.
        if inspect(self.db.get_bind()).has_table("agent_versions"):
            from app.models.agent_runtime import AgentVersion
            for version in self.db.query(AgentVersion).all():
                snapshot = version.config_snapshot or {}
                for binding in _list((snapshot.get("tools_config") or {}).get("skill_bindings")):
                    if isinstance(binding, dict) and binding.get("skill_id") == skill.id:
                        agent = agents.get(version.agent_id)
                        refs.append({"agent_id": version.agent_id,
                            "agent_name": agent.name if agent else snapshot.get("name", "已删除智能体"),
                            "version": binding.get("version"), "status": "published", "source": "published",
                            "agent_version": getattr(version, "version", None)})
        return refs

    def delete(self, skill: Skill):
        if self.references(skill):
            raise HTTPException(409, "技能仍被智能体引用，请先移除引用或归档")
        self.db.query(SkillTestRun).filter_by(skill_id=skill.id).delete()
        self.db.query(SkillVersion).filter_by(skill_id=skill.id).delete()
        self.db.query(SkillTool).filter_by(skill_id=skill.id).delete()
        self.db.delete(skill)
        self.db.commit()

    def catalog(self, user: User, ontology_id=None, ontology_version_id=None) -> dict:
        ontologies = self.db.query(ScenarioDict).order_by(ScenarioDict.sort_order).all()
        if ontology_id and not any(o.id == ontology_id for o in ontologies):
            raise HTTPException(404, "本体不存在")
        versions = self.db.query(OntologyVersion).filter_by(status="published")
        if ontology_id:
            versions = versions.filter_by(ontology_id=ontology_id)
        versions = versions.order_by(OntologyVersion.version_number.desc()).all()
        if ontology_version_id and not any(v.id == ontology_version_id for v in versions):
            raise HTTPException(422, "请选择关联本体的已发布版本")
        entity_query = self.db.query(OntologyEntity)
        if ontology_id:
            entity_query = entity_query.filter_by(ontology_id=ontology_id)
        entities = entity_query.all()
        if ontology_version_id:
            published_ids = {e.source_entity_id for e in self.db.query(OntologyVersionEntity).filter_by(
                version_id=ontology_version_id).all()}
            entities = [e for e in entities if e.id in published_ids]
        ids = {e.id for e in entities}
        functions = self.db.query(OntologyFunction).filter_by(status="active").all()
        actions = self.db.query(EntityAction).filter_by(status="active").all()
        def in_scope(tool):
            tool_ids = set(_list(getattr(tool, "entity_ids", None))) | ({tool.entity_id} if tool.entity_id else set())
            global_action = (isinstance(tool, EntityAction) and tool.category == "system"
                             and not tool_ids and ontology_version_id)
            return bool((global_action or (tool_ids and tool_ids.issubset(ids))) and
                        (not ontology_id or not tool.ontology_id or tool.ontology_id == ontology_id))
        functions, actions = [f for f in functions if in_scope(f)], [a for a in actions if in_scope(a)]
        if ontology_version_id:
            function_ids = {f.source_function_id for f in self.db.query(OntologyVersionFunction).filter_by(version_id=ontology_version_id).all()}
            action_ids = {a.source_action_id for a in self.db.query(OntologyVersionAction).filter_by(version_id=ontology_version_id).all()}
            functions = [f for f in functions if f.id in function_ids]
            actions = [a for a in actions if a.id in action_ids]
        ontology = self.db.get(ScenarioDict, ontology_id) if ontology_id else None
        assets = [a for a in self.db.query(Asset).filter_by(status="active").all()
                  if self._asset_allowed(a, ontology, ids)]
        return {"ontologies": [{"id": o.id, "code": o.code, "name": o.name} for o in ontologies],
            "ontology_versions": [{"id": v.id, "ontology_id": v.ontology_id,
                "version_number": v.version_number, "name": v.name, "status": v.status} for v in versions],
            "entities": [{"id": e.id, "name": e.name, "name_cn": e.name_cn, "ontology_id": e.ontology_id} for e in entities],
            "functions": [{"id": f.id, "name": f.name, "callable_name": f.callable_name,
                "entity_id": f.entity_id, "ontology_id": f.ontology_id, "input_schema": f.input_schema} for f in functions],
            "actions": [{"id": a.id, "name": a.name, "entity_id": a.entity_id,
                "ontology_id": a.ontology_id, "action_type": a.action_type} for a in actions],
            "assets": [{"id": a.id, "name": a.name, "kind": a.kind, "status": a.status,
                "description": a.description or ""} for a in assets]}
