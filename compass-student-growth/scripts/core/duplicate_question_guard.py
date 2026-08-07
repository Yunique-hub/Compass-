"""Field-level duplicate protection independent of question wording."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


class DuplicateQuestionGuard:
    def __init__(self, known_facts: Mapping[str, Any], asked_fields: Sequence[str] | None = None) -> None:
        self.known_facts = known_facts
        self.asked_fields = set(asked_fields or [])

    def is_known(self, field: str) -> bool:
        item = self.known_facts.get(field)
        if not isinstance(item, Mapping):
            return False
        return item.get("value") not in (None, "", [], {}) and float(item.get("confidence", 0)) >= 0.8

    def can_ask(self, field: str) -> bool:
        if field == "confirmed_direction":
            status = self.known_facts.get("direction_status")
            confirmed = isinstance(status, Mapping) and status.get("value") == "confirmed" and float(status.get("confidence", 0)) >= 0.8
            return not confirmed and field not in self.asked_fields
        aliases = {
            "skills_or_time_or_deadline": ("skills", "daily_learning_hours", "weekly_learning_hours", "deadline_time"),
            "time_availability": ("daily_learning_hours", "weekly_learning_hours"),
        }
        targets = aliases.get(field, (field,))
        return not any(self.is_known(target) for target in targets) and not any(target in self.asked_fields for target in targets)

    def filter_fields(self, fields: Sequence[str]) -> list[str]:
        return [field for field in fields if self.can_ask(field)]
