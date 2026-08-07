"""Contract shared by recruitment evidence providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import JobRecord


class RecruitmentProvider(ABC):
    name = "provider"

    @abstractmethod
    def collect(self, city: str, job: str, queries: list[str], context: dict[str, Any]) -> list[JobRecord]: ...

    def health(self) -> dict[str, Any]: return {"provider": self.name, "available": True}
