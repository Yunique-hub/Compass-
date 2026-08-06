"""基于显式评分与证据比较 2—4 个可逆就业方向。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .io_utils import result, run_cli
    from .models import CareerDirectionResult, clamp
except ImportError:
    from io_utils import result, run_cli
    from models import CareerDirectionResult, clamp

MODULE = "career_direction_analyzer"
ROOT = Path(__file__).resolve().parents[1]


def load_directions(path: Path | None = None) -> list[dict[str, Any]]:
    base = path or ROOT / "reference" / "career_directions"
    return [json.loads(item.read_text(encoding="utf-8")) for item in sorted(base.glob("*.json"))]


def calculate_fit(
    scores: Mapping[str, float],
    weights: Mapping[str, float],
    entry_cost_penalty: float,
) -> tuple[float, dict[str, float]]:
    breakdown = {key: clamp(scores.get(key, 0.0)) for key in weights}
    weighted = sum(breakdown[key] * float(weight) for key, weight in weights.items())
    return clamp(weighted - clamp(entry_cost_penalty)), breakdown


def analyze_directions(
    inputs: Mapping[str, Mapping[str, Any]],
    *,
    direction_ids: Sequence[str] | None = None,
    limit: int = 4,
) -> dict[str, Any]:
    rules = json.loads((ROOT / "config" / "plan_rules.json").read_text(encoding="utf-8"))
    weights = rules["direction_fit_weights"]
    allowed = set(direction_ids or [])
    results: list[CareerDirectionResult] = []
    for knowledge in load_directions():
        direction_id = knowledge["direction_id"]
        if allowed and direction_id not in allowed:
            continue
        item = inputs.get(direction_id, {})
        scores = item.get("scores", {})
        penalty = item.get("entry_cost_penalty", float(knowledge.get("entry_cost_score", 0.5)) * 0.10)
        fit, breakdown = calculate_fit(scores, weights, penalty)
        evidence = {key: list(item.get("evidence", {}).get(key, [])) for key in weights}
        missing = [key for key in weights if not evidence[key]]
        strengths = [text for key, texts in evidence.items() if breakdown[key] >= 0.6 for text in texts]
        results.append(CareerDirectionResult(
            direction_id=direction_id,
            direction_name=knowledge["direction_name"],
            fit_score=round(fit, 4),
            fit_breakdown=breakdown,
            evidence=evidence,
            missing_evidence=missing,
            current_strengths=strengths,
            risks=list(knowledge["risk_notes"]),
            entry_cost=knowledge.get("entry_cost_score", 0.5),
            exploration_task=knowledge["exploration_task"],
        ))
    results.sort(key=lambda item: (-item.fit_score, item.direction_id))
    selected = results[: max(2, min(4, limit))]
    return result(MODULE, {
        "stage": "当前为探索阶段",
        "score_interpretation": "适配分数仅用于方向比较，不是人格测评、就业概率或录用预测。",
        "directions": [item.to_dict() for item in selected],
        "next_state": "AWAITING_DIRECTION_CONFIRMATION",
    })


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return analyze_directions(raw.get("direction_inputs", {}), direction_ids=raw.get("direction_ids"), limit=int(raw.get("limit", 4)))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
