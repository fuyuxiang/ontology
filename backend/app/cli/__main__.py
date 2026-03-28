"""
模块功能：
- CLI 模块入口，支持 `python -m app.cli` 启动。
- 该文件位于 `backend/app/cli/__main__.py`，封装当前文件负责的后端能力，并向上层提供可复用接口。
"""

from app.cli.main import cli


if __name__ == "__main__":
    cli()
