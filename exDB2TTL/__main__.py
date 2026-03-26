"""模块执行入口，支持 `python -m exDB2TTL` 调用 CLI。"""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
