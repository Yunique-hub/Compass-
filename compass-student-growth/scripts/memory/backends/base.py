"""Backend contract for Compass persistent growth memory."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class MemoryBackend(ABC):
    @abstractmethod
    def load_user_context(self, user_id: str, *, query: str = "", top_k: int = 5) -> dict[str, Any]: ...

    @abstractmethod
    def save_profile(self, user_id: str, profile: Mapping[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def save_goal(self, user_id: str, goal: Mapping[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def save_competency(self, user_id: str, competency: Mapping[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def save_growth_state(self, user_id: str, state: Mapping[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def write_memory(self, user_id: str, memory: Mapping[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def retrieve_memory(self, user_id: str, query: str, *, top_k: int = 5) -> list[dict[str, Any]]: ...

    @abstractmethod
    def forget(self, user_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def health(self) -> dict[str, Any]: ...
