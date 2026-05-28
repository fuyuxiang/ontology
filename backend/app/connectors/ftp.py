"""FTP / SFTP 连接器。

FTP 用 stdlib ftplib（被动模式默认）。
SFTP 需要 paramiko；缺失时 test 给清晰错误。
Connection.params: {root_path, passive, use_tls}
credential: {username, password}
"""
from __future__ import annotations

from ftplib import FTP, FTP_TLS, error_perm
from typing import Any

try:
    import paramiko
    _HAS_PARAMIKO = True
except ImportError:
    _HAS_PARAMIKO = False


def _connect_ftp(host: str, port: int, params: dict, credential: dict | None):
    cred = credential or {}
    user = cred.get("username") or "anonymous"
    pwd = cred.get("password") or ""
    use_tls = bool(params.get("use_tls"))
    cls = FTP_TLS if use_tls else FTP
    ftp = cls()
    ftp.connect(host=host, port=port or 21, timeout=8)
    ftp.login(user=user, passwd=pwd)
    if use_tls:
        try:
            ftp.prot_p()
        except Exception:
            pass
    if not params.get("passive", True):
        ftp.set_pasv(False)
    return ftp


class FTPConnector:
    category = "file_transfer"
    type = "ftp"

    def test(self, *, params: dict, credential: dict | None) -> tuple[bool, str]:
        host = params.get("host")
        port = int(params.get("port") or 21)
        if not host:
            return False, "缺少 host 参数"
        try:
            ftp = _connect_ftp(host, port, params, credential)
            try:
                ftp.voidcmd("NOOP")
                return True, "连接成功"
            finally:
                ftp.quit()
        except error_perm as e:
            return False, f"FTP 权限错误: {e}"
        except Exception as e:
            return False, f"连接失败: {e}"

    def list_paths(self, *, params: dict, credential: dict | None,
                   path: str = "/", limit: int = 200) -> list[dict]:
        host = params.get("host")
        port = int(params.get("port") or 21)
        if not host:
            raise ValueError("缺少 host 参数")
        ftp = _connect_ftp(host, port, params, credential)
        try:
            target = path or params.get("root_path") or "/"
            ftp.cwd(target)
            entries: list[dict] = []
            ftp.retrlines("LIST", entries.append)
            results = []
            for line in entries[:limit]:
                parts = line.split(maxsplit=8)
                if len(parts) < 9:
                    continue
                perm, _, _, _, size, *rest = parts
                name = parts[-1]
                results.append({
                    "name": name,
                    "size": int(size) if size.isdigit() else 0,
                    "is_dir": perm.startswith("d"),
                })
            return results
        finally:
            ftp.quit()


class SFTPConnector:
    category = "file_transfer"
    type = "sftp"

    def test(self, *, params: dict, credential: dict | None) -> tuple[bool, str]:
        if not _HAS_PARAMIKO:
            return False, "缺少 paramiko 依赖（pip install paramiko）"
        host = params.get("host")
        port = int(params.get("port") or 22)
        if not host:
            return False, "缺少 host 参数"
        cred = credential or {}
        try:
            transport = paramiko.Transport((host, port))
            transport.connect(
                username=cred.get("username") or "",
                password=cred.get("password") or None,
            )
            sftp = paramiko.SFTPClient.from_transport(transport)
            try:
                sftp.listdir(params.get("root_path") or ".")
                return True, "连接成功"
            finally:
                sftp.close()
                transport.close()
        except Exception as e:
            return False, f"连接失败: {e}"

    def list_paths(self, *, params: dict, credential: dict | None,
                   path: str = "/", limit: int = 200) -> list[dict]:
        if not _HAS_PARAMIKO:
            raise RuntimeError("缺少 paramiko 依赖")
        host = params.get("host")
        port = int(params.get("port") or 22)
        cred = credential or {}
        transport = paramiko.Transport((host, port))
        transport.connect(
            username=cred.get("username") or "",
            password=cred.get("password") or None,
        )
        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            target = path or params.get("root_path") or "."
            attrs = sftp.listdir_attr(target)
            return [
                {
                    "name": a.filename,
                    "size": a.st_size or 0,
                    "is_dir": (a.st_mode or 0) & 0o040000 != 0,
                }
                for a in attrs[:limit]
            ]
        finally:
            sftp.close()
            transport.close()
