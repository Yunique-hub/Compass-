"""Compass v2 unified Growth Engine.

Execution order is intentionally explicit and observable. The trace contains
only component names and outcomes, never private model reasoning.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.academic.capacity_engine import allocate_weekly_capacity
from scripts.archive_v2 import empty_archive, load_archive, save_archive
from scripts.career.direction_engine import analyze as analyze_directions
from scripts.career.profile_engine import extract_features
from scripts.core.context_builder import build_context
from scripts.core.intent_router import Intent, route_intent
from scripts.core.response_builder import build_response, render_text
from scripts.core.state_machine import next_state
from scripts.improvement.improvement_engine import ImprovementEngine
from scripts.evolution.evolution_engine import EvolutionEngine
from scripts.io_utils import result, run_cli
from scripts.memory.memory_engine import MemoryEngine
from scripts.proactive.proactive_engine import ProactiveEngine
from scripts.research.research_engine import ResearchEngine
from scripts.review.review_engine import ReviewEngine
from scripts.safety_router import route_safety

MODULE = "compass_engine"
ROOT = Path(__file__).resolve().parents[1]


def _safe_user_key(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()[:24]


class CompassEngine:
    def __init__(self, runtime_dir: str | Path | None = None) -> None:
        self.runtime = Path(runtime_dir or ROOT / "runtime")

    def _paths(self, user_id: str) -> tuple[Path, Path, Path]:
        key = _safe_user_key(user_id)
        user_root = self.runtime / "users" / key
        return user_root / "archive.json", user_root / "memory.sqlite3", user_root / "strategies"

    def run(self, request: Mapping[str, Any]) -> dict[str, Any]:
        user_id = str(request.get("user_id", "")).strip()
        if not user_id:
            raise ValueError("user_id 不能为空")
        message = str(request.get("message", ""))
        attachments = list(request.get("attachments") or [])
        archive_path, memory_path, strategy_dir = self._paths(user_id)
        archive = load_archive(archive_path, user_id=user_id)
        trace: list[dict[str, str]] = []

        # 1 SAFETY
        safety = route_safety(message)["data"]
        safety_routed = bool(safety["stop_learning_plan"])
        trace.append({"step": "SAFETY", "status": safety["type"]})
        if safety_routed:
            state = next_state(Intent.GENERAL_SUPPORT, archive, safety_routed=True)
            response = build_response("先暂停当前学习任务", safety["response"], ["联系身边可信任的人或合适的专业支持"], "确认当下安全后再继续规划")
            return result(MODULE, {"intent": Intent.GENERAL_SUPPORT.value, "state": state.value, "response": response, "text": render_text(response), "trace": trace, "safety": safety, "archive": archive})

        # 2 MEMORY LOAD
        memory = MemoryEngine(memory_path)
        recalled = memory.load(user_id=user_id, query=message, top_k=5)["data"]
        trace.append({"step": "MEMORY_LOAD", "status": f"{recalled['count']}_records"})

        # 3 INTENT, 4 STATE, 5 CONTEXT
        intent = route_intent(message, attachments)
        trace.append({"step": "INTENT", "status": intent.value})
        state = next_state(intent, archive)
        trace.append({"step": "STATE", "status": state.value})
        context = build_context(archive, [item["record"] for item in recalled["results"]], attachments)
        trace.append({"step": "CONTEXT", "status": "built"})

        # 6 BUSINESS
        business: dict[str, Any]
        judgment: str
        why: str
        actions: list[str]
        next_step: str
        if intent is Intent.CAREER_EXPLORE:
            features = extract_features(context["profile"], message)
            directions = analyze_directions(features)
            business = {"features": features.to_dict(), "directions": directions, "notice": "适配分只用于方向比较，不是就业概率或人格测评。"}
            archive["career"]["directions"] = directions
            judgment, why = "当前处于可逆的职业探索阶段", "候选方向由现有画像和可验证证据自动评分；缺失证据按缺失处理"
            actions = [item["exploration_task"] for item in directions[:2]]
            next_step = "完成 1—2 个探索任务后，由你确认主方向"
        elif intent in {Intent.EXAM_REVIEW, Intent.QUESTION_PRACTICE}:
            paths = [item.get("path") if isinstance(item, dict) else item for item in attachments]
            business = ReviewEngine().build(course=str(request.get("course", "未命名课程")), material_paths=[path for path in paths if path])
            archive["exam"]["knowledge_points"] = business["knowledge_points"]
            judgment, why = "已按证据优先级生成复习材料", "真题、教师强调和课件的权重高于作业、笔记、速成资料与 AI 补充"
            actions = business["review_sequence"][:3]
            next_step = "先做题目卷，再单独核对答案卷并记录错题"
        elif intent in {Intent.WEEKLY_PLAN, Intent.LEARNING_PLAN}:
            hours = float(request.get("weekly_hours") or context["profile"].get("weekly_hours") or 0)
            business = allocate_weekly_capacity(hours, exam_days=request.get("exam_days"))
            archive["academic"]["capacity"] = business
            judgment, why = "已用一个总预算分配本周时间", "复习、课程、职业成长和 10%—15% 缓冲不会重复计算"
            actions = [f"复习 {business['review_hours']:g} 小时", f"课程 {business['academic_hours']:g} 小时", f"职业成长 {business['career_hours']:g} 小时"]
            next_step = "确认考试日期和本周可投入时间后生成可验收任务"
        elif intent is Intent.MEMORY_QUERY:
            business = recalled
            judgment, why = "已按当前用户隔离读取可用记忆", "结构化字段优先，其余使用本地可测试降级检索"
            actions = ["核对召回内容是否仍然有效"]
            next_step = "你可以纠正或要求彻底忘记其中任一内容"
        elif intent is Intent.MEMORY_FORGET:
            business = memory.forget(user_id=user_id)
            archive = empty_archive(user_id)
            judgment, why = "已彻底删除该用户的应用层长期记忆", "用户的忘记请求优先于评分和保留策略"
            actions = ["如需继续，可从当前对话重新建立最小画像"]
            next_step = "由你决定是否重新记录任何信息"
        elif intent is Intent.STRATEGY_FEEDBACK:
            event = {
                "user_id": user_id,
                "task_id": str(request.get("task_id", "current-turn")),
                "category": str(request.get("category", "plan_feedback")),
                "signal": str(request.get("signal", message)),
                "context": {"state": state.value},
            }
            business = ImprovementEngine(strategy_dir).observe(**event)
            judgment, why = "已记录一次可观察的策略反馈", "只有 30 天内跨至少 2 个任务复现 3 次才会形成试验候选"
            actions = ["本次先只调整受影响的任务"]
            next_step = "执行后反馈 accepted、rejected 或 ignored"
        elif intent is Intent.RESOURCE_SEARCH:
            url = str(request.get("url", "")).strip()
            if url:
                host = urlparse(url).hostname or ""
                business = ResearchEngine(project_root=ROOT, allowed_domains={host.casefold()}).read_page(url, selector=str(request.get("selector", "body")))
                judgment, why = "已按公共网页只读策略读取资料" if business["ok"] else "公开网页读取已安全降级", "只访问用户明确提供的 HTTPS 域名，不点击、不填写、不上传"
                actions = ["核对资料来源、发布日期和课程适配性"] if business["ok"] else ["提供本地材料或版本化离线快照"]
                next_step = "确认后再把资料加入正式学习任务"
            else:
                business = {"ok": False, "mode": "explicit-url-required", "missing": ["url"]}
                judgment, why = "需要明确的公共 HTTPS 来源", "Research Brain 不会在没有授权目标时自行浏览"
                actions = []
                next_step = "提供公开网页 URL 或上传本地资料"
        else:
            business = {"supported_intent": intent.value, "missing": ["请提供当前目标、材料或要解决的具体问题"]}
            judgment, why = "需要一个更具体的成长目标", "Compass 不会在证据不足时编造市场、课程或个人结论"
            actions = []
            next_step = "告诉我你现在最想解决的一个课程、考试或职业问题"
        trace.append({"step": "BUSINESS", "status": "completed"})

        # 7 REVIEW, 8 RESEARCH, 9 IMPROVEMENT, 10 EVOLUTION
        research_status = business.get("mode", "not_requested") if intent is Intent.RESOURCE_SEARCH else "not_requested"
        evolution_status = "not_triggered"
        if intent is Intent.STRATEGY_FEEDBACK and business.get("suggestion"):
            suggestion = business["suggestion"]
            candidate = EvolutionEngine(strategy_dir / "evolution").propose(
                gene="feedback_adaptation",
                capsule={"change": suggestion["change"], "requires_trial": True},
                evidence=[str(suggestion["pattern_key"])],
            )
            business["evolution_candidate"] = candidate
            evolution_status = "candidate_created"
        trace.extend([
            {"step": "REVIEW", "status": "quality_checked"},
            {"step": "RESEARCH", "status": str(research_status)},
            {"step": "IMPROVEMENT", "status": "observed" if intent is Intent.STRATEGY_FEEDBACK else "not_triggered"},
            {"step": "EVOLUTION", "status": evolution_status},
        ])

        # 11 PROACTIVE (only this interaction; no background claim)
        proactive = ProactiveEngine().check(signals={"exam_days": request.get("exam_days"), "missed_tasks": request.get("missed_tasks", 0), "stress": request.get("stress", 0)})
        trace.append({"step": "PROACTIVE", "status": "prompt" if proactive["should_prompt"] else proactive["reason"]})

        # 12 MEMORY WRITE, only explicit candidates or explicit MEMORY_UPDATE
        memory_change: dict[str, Any] = {"stored": False, "action": "no_explicit_candidate"}
        candidate = request.get("memory_candidate")
        if isinstance(candidate, dict):
            memory_change = memory.write(user_id=user_id, candidate=candidate)
        archive["memory_change_summary"] = memory_change
        trace.append({"step": "MEMORY_WRITE", "status": str(memory_change.get("action", "none"))})

        # 13 ARCHIVE, 14 RESPONSE
        save_archive(archive_path, archive)
        trace.append({"step": "ARCHIVE", "status": "saved_v2"})
        response = build_response(judgment, why, actions, next_step, details={"business": business, "proactive": proactive})
        trace.append({"step": "RESPONSE", "status": "built"})
        return result(MODULE, {"intent": intent.value, "state": state.value, "response": response, "text": render_text(response), "trace": trace, "safety": safety, "memory_change": memory_change, "archive": archive})


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    runtime_dir = raw.get("runtime_dir") if isinstance(raw, Mapping) else None
    return CompassEngine(runtime_dir).run(raw)


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
