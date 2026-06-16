from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    success: bool
    message: str
    output: dict | None = None


class BaseActionExecutor(ABC):
    @abstractmethod
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        pass

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> dict:
        pass

    @classmethod
    @abstractmethod
    def get_label(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        pass
