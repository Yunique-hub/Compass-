"""Optional LLM boundary; deterministic engines never require an LLM."""

from __future__ import annotations

from typing import Protocol, Sequence


class LLMAdapter(Protocol):
    def complete(self, prompt: str, *, evidence: Sequence[str] = ()) -> str: ...


class DisabledLLMAdapter:
    def complete(self, prompt: str, *, evidence: Sequence[str] = ()) -> str:
        raise RuntimeError("LLM_DISABLED")

