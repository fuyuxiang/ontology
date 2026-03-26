"""exDB2TTL 命令行入口，串联抽取、生成、校验与同步流程。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backend_sync import sync_backend_profile
from .config import ConfigError, create_bootstrap_config, load_project_config
from .drafts import parse_draft_bundle, serialize_draft_bundle
from .llm import call_llm
from .metadata import extract_metadata
from .prompts import build_messages, render_prompt_text
from .validate import validate_bundle


def main(argv: list[str] | None = None) -> int:
    """解析命令行参数并分发到具体子命令。"""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}")
        return 2
    except Exception as exc:  # pragma: no cover - CLI safety
        print(f"ERROR: {exc}")
        return 1


def _build_parser() -> argparse.ArgumentParser:
    """构建 CLI 子命令结构。"""
    parser = argparse.ArgumentParser(prog="exDB2TTL", description="Database metadata to ontology draft pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="Create an initial project config from database and table names")
    bootstrap.add_argument("--database-name", required=True)
    bootstrap.add_argument("--dialect", default="sqlite")
    bootstrap.add_argument("--table", dest="tables", action="append", required=True)
    bootstrap.add_argument("--output-dir", default="exDB2TTL/out")
    bootstrap.add_argument("--config-path", default="exDB2TTL/project.json")
    bootstrap.set_defaults(func=_cmd_bootstrap)

    extract = subparsers.add_parser("extract", help="Extract live database metadata")
    extract.add_argument("--config", required=True)
    extract.set_defaults(func=_cmd_extract)

    draft = subparsers.add_parser("draft", help="Build the prompt, call the LLM, and save draft outputs")
    draft.add_argument("--config", required=True)
    draft.add_argument("--metadata-path")
    draft.set_defaults(func=_cmd_draft)

    validate = subparsers.add_parser("validate", help="Validate ontology and SHACL drafts with sample RDF")
    validate.add_argument("--config", required=True)
    validate.add_argument("--metadata-path")
    validate.add_argument("--drafts-path")
    validate.set_defaults(func=_cmd_validate)

    sync_backend = subparsers.add_parser(
        "sync-backend",
        help="Sync generated ontology, SHACL, and rules artifacts into the current backend profile",
    )
    sync_backend.add_argument("--config", required=True)
    sync_backend.add_argument("--drafts-path")
    sync_backend.set_defaults(func=_cmd_sync_backend)

    run = subparsers.add_parser("run", help="Run extract, draft, validate, and export artifacts")
    run.add_argument("--config", required=True)
    run.set_defaults(func=_cmd_run)

    return parser


def _cmd_bootstrap(args: argparse.Namespace) -> int:
    """生成最小可用项目配置与元数据补充清单。"""
    config_path = Path(args.config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = create_bootstrap_config(
        database_name=args.database_name,
        tables=args.tables,
        dialect=args.dialect.lower(),
        output_dir=args.output_dir,
    )
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    request_path = config_path.parent / "metadata-request.md"
    request_path.write_text(
        _metadata_request_text(args.database_name, args.tables, args.dialect.lower()),
        encoding="utf-8",
    )
    print(f"Wrote bootstrap config: {config_path}")
    print(f"Wrote metadata checklist: {request_path}")
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    """抽取数据库元数据并写出 `metadata.json`。"""
    config = load_project_config(args.config)
    output_dir = _ensure_output_dir(config.output_dir)
    metadata = extract_metadata(config.database)
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote metadata: {metadata_path}")
    return 0


def _cmd_draft(args: argparse.Namespace) -> int:
    """构建提示词、调用模型并保存草稿产物。"""
    config = load_project_config(args.config)
    output_dir = _ensure_output_dir(config.output_dir)
    metadata = _load_or_extract_metadata(config, args.metadata_path)

    messages = build_messages(config, metadata)
    prompt_path = output_dir / "prompt.txt"
    prompt_path.write_text(render_prompt_text(messages), encoding="utf-8")

    raw_response = call_llm(config.llm, messages)
    raw_response_path = output_dir / "drafts.raw.txt"
    raw_response_path.write_text(raw_response, encoding="utf-8")

    bundle = parse_draft_bundle(raw_response)
    _write_bundle_files(bundle, output_dir)
    drafts_json_path = output_dir / "drafts.json"
    drafts_json_path.write_text(serialize_draft_bundle(bundle), encoding="utf-8")

    print(f"Wrote prompt: {prompt_path}")
    print(f"Wrote raw LLM response: {raw_response_path}")
    print(f"Wrote draft bundle: {drafts_json_path}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """校验生成的本体、SHACL 与规则文件。"""
    config = load_project_config(args.config)
    output_dir = _ensure_output_dir(config.output_dir)
    metadata = _load_or_extract_metadata(config, args.metadata_path)
    bundle = _load_bundle(output_dir, args.drafts_path)

    artifacts = validate_bundle(config, metadata, bundle, output_dir)
    validation_path = output_dir / "validation-summary.json"
    validation_path.write_text(json.dumps(artifacts.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote validation summary: {validation_path}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """执行完整流水线：抽取、生成、校验，并按需同步后端。"""
    config = load_project_config(args.config)
    output_dir = _ensure_output_dir(config.output_dir)

    metadata = extract_metadata(config.database)
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    messages = build_messages(config, metadata)
    prompt_path = output_dir / "prompt.txt"
    prompt_path.write_text(render_prompt_text(messages), encoding="utf-8")

    raw_response = call_llm(config.llm, messages)
    raw_response_path = output_dir / "drafts.raw.txt"
    raw_response_path.write_text(raw_response, encoding="utf-8")

    bundle = parse_draft_bundle(raw_response)
    _write_bundle_files(bundle, output_dir)
    drafts_json_path = output_dir / "drafts.json"
    drafts_json_path.write_text(serialize_draft_bundle(bundle), encoding="utf-8")

    artifacts = validate_bundle(config, metadata, bundle, output_dir)
    validation_path = output_dir / "validation-summary.json"
    validation_path.write_text(json.dumps(artifacts.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote metadata: {metadata_path}")
    print(f"Wrote prompt: {prompt_path}")
    print(f"Wrote raw LLM response: {raw_response_path}")
    print(f"Wrote drafts: {drafts_json_path}")
    print(f"Wrote validation summary: {validation_path}")
    if config.backend_sync.enabled:
        synced = sync_backend_profile(config, output_dir, bundle)
        print(f"Synced backend profile: {synced['profile_root']}")
        if config.backend_sync.activate_profile:
            print(f"Activated backend profile: {synced['active_profile_path']}")
    return 0


def _cmd_sync_backend(args: argparse.Namespace) -> int:
    """把已生成产物同步到后端 profile 目录。"""
    config = load_project_config(args.config)
    output_dir = _ensure_output_dir(config.output_dir)
    bundle = _load_bundle(output_dir, args.drafts_path)

    synced = sync_backend_profile(config, output_dir, bundle)
    print(f"Synced backend profile: {synced['profile_root']}")
    if config.backend_sync.activate_profile:
        print(f"Activated backend profile: {synced['active_profile_path']}")
    return 0


def _ensure_output_dir(path: Path) -> Path:
    """确保输出目录存在。"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_or_extract_metadata(config, metadata_path: str | None):
    """优先复用已有 metadata.json，缺失时再走实时抽取。"""
    if metadata_path:
        payload = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        from .models import ColumnMeta, DatabaseMetadata, ForeignKeyMeta, TableMeta

        return DatabaseMetadata(
            database_name=payload["database_name"],
            dialect=payload["dialect"],
            schema=payload.get("schema"),
            tables=[
                TableMeta(
                    name=table["name"],
                    columns=[ColumnMeta(**column) for column in table.get("columns", [])],
                    primary_keys=table.get("primary_keys", []),
                    foreign_keys=[ForeignKeyMeta(**fk) for fk in table.get("foreign_keys", [])],
                    comment=table.get("comment"),
                    sample_rows=table.get("sample_rows", []),
                )
                for table in payload.get("tables", [])
            ],
        )
    return extract_metadata(config.database)


def _load_bundle(output_dir: Path, drafts_path: str | None):
    """读取草稿包，默认从输出目录中的 `drafts.json` 加载。"""
    source_path = Path(drafts_path) if drafts_path else output_dir / "drafts.json"
    return parse_draft_bundle(source_path.read_text(encoding="utf-8"))


def _write_bundle_files(bundle, output_dir: Path) -> None:
    """把草稿包拆分写成后续流程需要的独立文件。"""
    (output_dir / "telecom-porting.ttl").write_text(bundle.telecom_ontology_ttl + "\n", encoding="utf-8")
    (output_dir / "telecom-shapes.ttl").write_text(bundle.telecom_shacl_ttl + "\n", encoding="utf-8")
    (output_dir / "mapping.csv").write_text(bundle.mapping_csv + "\n", encoding="utf-8")
    (output_dir / "porting-risk.yaml").write_text(bundle.rules_yaml + "\n", encoding="utf-8")
    (output_dir / "business-rules.md").write_text(bundle.business_rules_markdown + "\n", encoding="utf-8")


def _metadata_request_text(database_name: str, tables: list[str], dialect: str) -> str:
    """生成补充元数据所需的信息清单。"""
    table_lines = "\n".join(f"- {table}" for table in tables)
    return f"""# Metadata Checklist

当前项目只知道数据库名和表名时，代码可以先 bootstrap，但还不能直接做完整元数据抽取。

数据库:
- 名称: {database_name}
- 方言: {dialect}

表:
{table_lines}

要完成自动化流程，至少还需要以下三种输入中的一种:
1. SQLite / MySQL 直连信息
2. 每张表一个同名 CSV 样例文件
3. DBA 导出的完整 metadata.json

如果只有 CSV，主键、外键、注释通常无法自动恢复，代码会按“弱元数据模式”继续往下跑。
"""
