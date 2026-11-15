from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class AdapterResult:
    status: str
    records_read: int = 0
    records_written: int = 0
    error_code: str = ""

class IntegrationAdapter(ABC):
    """Provider adapter contract. Concrete adapters must be separately reviewed."""
    @abstractmethod
    def health_check(self) -> AdapterResult: ...
    @abstractmethod
    def execute(self, operation: str, payload: dict[str, Any]) -> AdapterResult: ...

class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, IntegrationAdapter] = {}
    def register(self, provider: str, adapter: IntegrationAdapter):
        self._adapters[provider] = adapter
    def get(self, provider: str) -> IntegrationAdapter | None:
        return self._adapters.get(provider)

registry = AdapterRegistry()
