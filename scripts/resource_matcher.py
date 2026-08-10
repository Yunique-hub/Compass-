"""从已核验本地资源元数据中匹配少量学习资源。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .io_utils import error, result, run_cli
except ImportError:
    from io_utils import error, result, run_cli

MODULE = "resource_matcher"
ROOT = Path(__file__).resolve().parents[1]


def load_resources() -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for path in sorted((ROOT / "reference" / "resources").glob("*_resources.json")):
        resources.extend(json.loads(path.read_text(encoding="utf-8")).get("resources", []))
    return resources


def match_resources(
    competencies: Sequence[str], *, stage: str = "入门", max_hours: float = 8.0,
    learning_preferences: Sequence[str] | None = None, minimum: int = 2, maximum: int = 4,
) -> dict[str, Any]:
    wanted = set(competencies)
    preferences = set(learning_preferences or [])
    ranked: list[tuple[int, dict[str, Any]]] = []
    warnings: list[dict[str, Any]] = []
    for item in load_resources():
        if not item.get("verified"):
            warnings.append(error("UNVERIFIED_RESOURCE", "未核验资源不会进入正式推荐。", resource_id=item["resource_id"]))
            continue
        overlap = len(wanted.intersection(item.get("recommended_for", [])))
        stage_score = 1 if item.get("stage") == stage else 0
        time_score = 1 if float(item.get("estimated_hours", 0)) <= max_hours else 0
        preference_score = 1 if item.get("resource_type") in preferences else 0
        if overlap or not wanted:
            ranked.append((overlap * 10 + stage_score * 2 + time_score + preference_score, item))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["resource_id"]))
    selected = [item for _, item in ranked[:maximum]]
    if wanted and len(selected) < minimum:
        warnings.append(error("INSUFFICIENT_RELEVANT_RESOURCES", "相关资源少于期望数量；为避免跨领域串线，不使用无关资源补齐。", requested_minimum=minimum, relevant_count=len(selected)))
    return result(MODULE, {"resources": selected[:maximum], "count": min(len(selected), maximum)}, warnings=warnings)


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return match_resources(raw.get("competencies", []), stage=raw.get("stage", "入门"), max_hours=float(raw.get("max_hours", 8)), learning_preferences=raw.get("learning_preferences", []), minimum=int(raw.get("minimum", 2)), maximum=int(raw.get("maximum", 4)))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
