"""Direct knowledge answers with an injectable model boundary and safe offline fallback."""
from __future__ import annotations

import re
from typing import Mapping

from .llm_adapter import LLMAdapter


STABLE_CONCEPTS: Mapping[str, str] = {
    "机会成本": "机会成本是做出一个选择时，放弃的所有替代方案中价值最高的那个。它不是所有放弃项的总和，而是最佳替代方案的价值。",
    "p值": "p 值是在零假设和统计模型成立时，观察到当前结果或更极端结果的概率。它不是零假设为真的概率，也不能单独表示效应大小。",
    "wacc": "WACC 是加权平均资本成本，按债务和权益在资本结构中的权重，合并税后债务成本与权益成本。DCF 中通常用它折现与全部资本提供者对应的 FCFF。",
    "irac": "IRAC 是法律分析结构：Issue（争点）、Rule（规则）、Application（把规则适用于事实）和 Conclusion（结论）。关键不只是列法条，而是说明规则为何适用于具体事实。",
    "python list和tuple的区别": "Python 的 list 可增删改，适合会变化的数据；tuple 通常不可修改，适合固定记录。元素均可哈希时，tuple 还可以作为字典键。",
}


def extract_concept(message: str) -> str:
    text = str(message or "").strip(" \t\r\n？?")
    patterns = (
        r"^(?:什么是|何为)\s*(.+)$",
        r"^(.+?)(?:是什么|是什么意思|怎么理解)$",
        r"^(.+?)(?:有什么区别|有何区别)$",
    )
    for pattern in patterns:
        match = re.match(pattern, text, re.I)
        if match:
            return match.group(1).strip()
    return text


def _normalize(concept: str) -> str:
    return re.sub(r"[\s_（）()·，,。.]", "", concept).casefold()


class DirectAnswerHandler:
    def __init__(self, adapter: LLMAdapter | None = None) -> None:
        self.adapter = adapter

    def answer(self, message: str) -> str:
        concept = extract_concept(message)
        if self.adapter is not None:
            try:
                answer = self.adapter.complete(
                    f"直接、准确地解释“{concept}”，给出核心定义、一个必要辨析和一个简短例子；不要启动用户画像或成长规划。"
                ).strip()
                if answer:
                    return answer
            except RuntimeError:
                pass
        normalized = _normalize(concept)
        for key, answer in STABLE_CONCEPTS.items():
            if _normalize(key) == normalized:
                return answer
        return f"“{concept}”需要由通用知识模型直接解释；当前离线运行时没有足够可靠的内置定义，因此不会编造，也不会启动成长规划。"
