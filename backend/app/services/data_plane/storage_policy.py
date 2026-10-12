"""Use the saved upload configuration at the document ingress boundary."""
from pathlib import Path

from app.config import settings
from app.models.system_config import SystemConfig


def storage_policy(db):
    rows = db.query(SystemConfig).filter_by(group="storage").all()
    cfg = {r.key.removeprefix("storage."): r.value for r in rows}
    from app.api.v1.system_config import _get_config_value
    try:
        maximum = int(_get_config_value(db, "storage.max_upload_mb") or 50) * 1024 * 1024
    except (TypeError, ValueError) as exc:
        raise ValueError("storage.max_upload_mb 必须为正整数") from exc
    if maximum < 1:
        raise ValueError("storage.max_upload_mb 必须为正整数")
    allowed = {x.strip().lower().lstrip(".") for x in (cfg.get("allowed_types") or
        ".owl,.rdf,.ttl,.csv,.xls,.xlsx,.json,.doc,.docx,.ppt,.pptx,.pdf,.txt,.md,.png,.jpg,.jpeg,.gif,.mp4,.avi,.mov").split(",") if x.strip()}
    backend = cfg.get("backend") or "local"
    if backend not in ("local", "minio", "oss"):
        raise ValueError(f"不支持的存储后端: {backend}")
    local_path = Path(cfg.get("local_path") or "./uploads").expanduser()
    if not local_path.is_absolute():
        local_path = Path(__file__).resolve().parents[3] / local_path
    return {"backend": backend, "max_bytes": maximum, "allowed": allowed,
            "local_path": local_path.resolve(),
            "endpoint": cfg.get("endpoint") or settings.MINIO_ENDPOINT,
            "bucket": cfg.get("bucket") or settings.MINIO_BUCKET,
            "access_key": cfg.get("access_key") or settings.MINIO_ACCESS_KEY,
            "secret_key": cfg.get("secret_key") or settings.MINIO_SECRET_KEY}


def managed_local_path(db, path, *, directory=False):
    """Resolve only administrator-managed roots, including the historic upload root."""
    target = Path(path or "").expanduser().resolve()
    roots = [storage_policy(db)["local_path"], Path(__file__).resolve().parents[3] / "uploads"]
    if directory and getattr(settings, "LOCAL_DATA_ROOT", None):
        roots.append(Path(settings.LOCAL_DATA_ROOT).expanduser().resolve())
    for root in roots:
        try:
            target.relative_to(root.resolve())
            return target
        except ValueError:
            continue
    raise ValueError("本地文档路径不属于受管上传/数据目录，请管理员配置目录或使用上传入口")
