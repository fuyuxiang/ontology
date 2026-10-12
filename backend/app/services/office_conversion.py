"""Convert legacy Office uploads in an isolated, disposable headless profile."""
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import settings

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_FORMATS = {"doc": "docx", "xls": "xlsx", "ppt": "pptx"}


def convert_legacy_office(content: bytes, source_extension: str) -> bytes:
    target = _FORMATS.get(source_extension.lower())
    if target is None:
        raise ValueError("不支持的 Office 转换类型")
    executable = settings.OFFICE_CONVERTER or shutil.which("soffice")
    if not executable:
        raise ValueError("旧版 Office 文档需要 LibreOffice；请安装 soffice 或配置 OFFICE_CONVERTER")
    with tempfile.TemporaryDirectory(prefix="ontology-office-") as directory:
        path = Path(directory)
        source = path / f"document.{source_extension}"
        source.write_bytes(content)
        try:
            process = subprocess.run([
                executable, f"-env:UserInstallation={(path / 'profile').as_uri()}",
                "--headless", "--nologo", "--nodefault", "--norestore",
                "--convert-to", target, "--outdir", str(path), str(source),
            ], cwd=path, capture_output=True, timeout=settings.OFFICE_CONVERSION_TIMEOUT_SECONDS, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Office 文档转换超时，请检查文件或重试") from exc
        except OSError as exc:
            raise ValueError("无法启动 Office 转换器，请检查 OFFICE_CONVERTER") from exc
        output = path / f"document.{target}"
        if process.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            raise ValueError("Office 文档转换失败，文件可能损坏或转换器不可用")
        return output.read_bytes()
