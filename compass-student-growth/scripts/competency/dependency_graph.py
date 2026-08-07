"""Small acyclic learning-dependency helper."""
from __future__ import annotations

from typing import Iterable


class DependencyGraph:
    def __init__(self, edges: Iterable[tuple[str, str]] = ()) -> None: self.edges = list(edges)
    def prerequisites(self, skill: str) -> list[str]: return [source for source, target in self.edges if target == skill]
    def ready(self, skill: str, verified: set[str]) -> bool: return all(item in verified for item in self.prerequisites(skill))
