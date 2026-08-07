"""Compass 2.2 market-driven, evidence-first Growth Engine.

The user-facing response never exposes profile scores, internal field names or
reasoning traces. Development traces contain only observable state and actions.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.academic.capacity_engine import calculate_realistic_capacity
from scripts.archive_v2 import empty_archive, load_archive, save_archive
from scripts.career.direction_engine import analyze as analyze_directions
from scripts.career.profile_engine import extract_features
from scripts.core.action_selector import MentorAction
from scripts.core.context_builder import build_context
from scripts.core.goal_planner import build_goal_plan
from scripts.core.interaction_trace import write_interaction_trace
from scripts.core.intent_router import Intent, route_intent
from scripts.core.known_facts import extract_known_facts, fact_value, merge_known_facts
from scripts.core.mentor_diagnosis import build_mentor_diagnosis
from scripts.core.mentor_response_builder import action_response, ask_name_response, quick_profile_response, stage_question_response
from scripts.core.onboarding_engine import evaluate_onboarding
from scripts.core.question_policy import select_questions
from scripts.evolution.evolution_engine import EvolutionEngine
from scripts.improvement.improvement_engine import ImprovementEngine
from scripts.growth_orchestrator import GrowthOrchestrator
from scripts.io_utils import result, run_cli
from scripts.memory.memory_engine import MemoryEngine
from scripts.proactive.proactive_engine import ProactiveEngine
from scripts.research.research_engine import ResearchEngine
from scripts.review.review_engine import ReviewEngine
from scripts.safety_router import route_safety

MODULE = "compass_engine"
ROOT = Path(__file__).resolve().parents[1]
LEGACY_TRACE = [
    "SAFETY", "MEMORY_LOAD", "INTENT", "STATE", "CONTEXT", "BUSINESS", "REVIEW",
    "RESEARCH", "IMPROVEMENT", "EVOLUTION", "PROACTIVE", "MEMORY_WRITE", "ARCHIVE", "RESPONSE",
]


def _safe_user_key(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()[:24]


def _trace(statuses: Mapping[str, str]) -> list[dict[str, str]]:
    return [{"step": step, "status": str(statuses.get(step, "not_triggered"))} for step in LEGACY_TRACE]


def _profile_from_facts(facts: Mapping[str, Any]) -> dict[str, Any]:
    profile: dict[str, Any] = {}
    for key in ("preferred_name", "education_level", "grade", "major", "primary_need", "daily_learning_hours", "weekly_learning_hours", "company_preference"):
        value = fact_value(facts, key)
        if value not in (None, "", [], {}):
            profile[key] = value
    skills = list(fact_value(facts, "skills", []))
    if skills:
        profile["claimed_skills"] = skills
        profile["courses"] = skills
    interests = []
    if fact_value(facts, "coding_interest"):
        interests.append("喜欢写代码")
    if "Python" in skills:
        interests.append("Python")
    if interests:
        profile["interests"] = interests
    daily = fact_value(facts, "daily_learning_hours")
    weekly = fact_value(facts, "weekly_learning_hours")
    if daily is not None:
        profile["weekly_hours"] = float(daily) * 7
    elif weekly is not None:
        profile["weekly_hours"] = float(weekly)
    return profile


def _direction_ids(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    mapping = {"IT支持": "it-support", "网络运维": "network-operations", "DevOps Support": "devops-support"}
    return [mapping[item] for item in values if item in mapping]


def _prioritize_directions(directions: list[dict[str, Any]], facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    explicit = _direction_ids(fact_value(facts, "career_direction", []))
    excluded = set(_direction_ids(fact_value(facts, "excluded_direction", [])))
    status = str(fact_value(facts, "direction_status", "candidate"))
    for item in directions:
        if item["direction_id"] in explicit:
            item["direction_status"] = status
            item["is_confirmed"] = status == "confirmed"
        else:
            item["direction_status"] = "candidate"
    active = [item for item in directions if item["direction_id"] not in excluded]
    return sorted(active, key=lambda item: (item["direction_id"] not in explicit, -item["fit_score"], item["direction_id"]))


def _question_history(archive: Mapping[str, Any]) -> dict[str, Any]:
    raw = archive.get("question_history") or {}
    return {"asked_fields": list(raw.get("asked_fields") or []), "question_only_streak": int(raw.get("question_only_streak", 0))}


def _record_questions(history: dict[str, Any], fields: Sequence[str], *, question_only: bool) -> None:
    history["asked_fields"] = list(dict.fromkeys([*history.get("asked_fields", []), *fields]))
    history["question_only_streak"] = min(2, int(history.get("question_only_streak", 0)) + 1) if question_only else 0


def _memory_candidate(user_id: str, key: str, item: Mapping[str, Any]) -> dict[str, Any]:
    importance = 1.0 if key in {"preferred_name", "career_direction", "direction_status", "target_city", "target_job"} else 0.8
    return {
        "candidate_id": f"profile-{key}", "record_id": f"profile-{key}", "user_id": user_id,
        "memory_type": "explicit_profile" if key in {"preferred_name", "preferred_name_usage"} else "profile_fact",
        "content": {"key": key, "value": item.get("value"), "user_explicit": True, "confirmed": True},
        "importance": importance, "stability": 0.9, "future_relevance": 0.9,
        "user_explicitness": 1.0, "recurrence": 0.5, "confidence": float(item.get("confidence", 1.0)),
        "task_value": 0.9, "user_intent": "",
    }


def _write_explicit_facts(memory: MemoryEngine, user_id: str, incoming: Mapping[str, Any]) -> dict[str, Any]:
    changes = []
    for key, item in incoming.items():
        stored = memory.write(user_id=user_id, candidate=_memory_candidate(user_id, key, item))
        changes.append({"key": key, "stored": bool(stored.get("stored")), "action": stored.get("action")})
    return {"stored": any(item["stored"] for item in changes), "changes": changes, "action": "explicit_profile_update" if changes else "no_new_fact"}


def _progress_response(name: str, archive: Mapping[str, Any], usage: bool) -> dict[str, Any]:
    prefix = f"{name}，" if name and usage else ""
    plan = archive.get("academic", {}).get("current_plan") or {}
    goal = plan.get("primary_goal") or archive.get("career", {}).get("confirmed_goal", {}).get("primary_direction") or "上次的成长目标"
    text = (
        f"{prefix}我们不重新建档，直接从上次进度继续。\n"
        f"当前主线：{goal}。\n"
        "这次请只告诉我三件事：完成了哪些、实际用了多久、哪个最卡。我会据此调整下一周任务量。"
    )
    return {"current_judgment": "继续上次计划", "why": "已恢复称呼、阶段和当前计划", "do_now": ["汇报完成项、实际用时和最大卡点"], "next_step": "根据真实完成率调整容量", "mentor_sections": {"returning_user_resume": text}, "text": text}


def _career_explore_response(name: str, usage: bool, stage: Mapping[str, Any], directions: Sequence[Mapping[str, Any]], questions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    prefix = f"{name}，" if name and usage else ""
    lines = [f"{prefix}你现在处于{stage.get('label', '职业探索阶段')}，已经不需要再从头填写资料。", "根据现有专业、课程和技能基础，值得优先比较："]
    for index, item in enumerate(directions[:3], 1):
        language = "你已经明确选择" if item.get("is_confirmed") else "值得重点探索"
        lines.append(f"{index}. {item['direction_name']}：{language}；先做：{item['exploration_task']}")
    if questions:
        lines.append("现在只剩会直接影响第一周任务的关键点：")
        lines.extend(f"{index}. {item['text']}" for index, item in enumerate(questions, 1))
    text = "\n".join(lines)
    return {
        "current_judgment": f"当前是{stage.get('label', '职业探索阶段')}",
        "why": "候选方向来自现有专业、技能和兴趣证据",
        "do_now": [item["exploration_task"] for item in directions[:2]],
        "next_step": "确认一个主方向和稳定时间后立即生成阶段与本周计划",
        "mentor_sections": {"direction_candidates": [item["direction_name"] for item in directions[:3]], "questions": [item["text"] for item in questions]},
        "text": text,
    }


def _exam_plan(course: str, materials: list[str], exam_days: int | None) -> dict[str, Any]:
    tasks = [
        {"title": "列出考试知识点优先级", "why": "先确定有限时间内的覆盖顺序", "estimated_time": 2, "specific_action": ["按章节列知识点", "标记真题和教师强调", "选出前三个薄弱点"], "output": ["review-map.md"], "acceptance_criteria": ["至少列出 10 个知识点并标优先级"], "evidence": "复习地图", "fallback": "无材料时按课程目录建立临时版本"},
        {"title": "完成一轮限时练习", "why": "用答题结果代替重复阅读", "estimated_time": 3, "specific_action": ["完成一组题", "独立作答", "核对并标错因"], "output": ["答题记录"], "acceptance_criteria": ["每道错题有知识点和错因"], "evidence": "答案与批改", "fallback": "没有题库时先做课后题"},
        {"title": "重做最高频错题", "why": "把反馈转成可验证掌握度", "estimated_time": 2, "specific_action": ["隔开答案重做", "口头解释关键步骤"], "output": ["错题重做记录"], "acceptance_criteria": ["重做正确并能解释"], "evidence": "重做结果", "fallback": "先重做最重要的 3 道"},
    ]
    return {"plan_type": "REVIEW_PLAN", "primary_goal": f"在{f'未来 {exam_days} 天' if exam_days is not None else '当前复习周期'}完成{course or '这门课'}的重点覆盖、练习反馈和错题重做", "goal_horizon": f"{exam_days} 天" if exam_days is not None else "本周", "stage_goals": [{"period": "现在", "goal": "重点识别"}, {"period": "中段", "goal": "限时练习"}, {"period": "考前", "goal": "错题重做"}], "current_stage_goal": "先完成复习地图", "week_goal": "完成重点、练习和错题闭环", "weekly_core_tasks": tasks, "optional_tasks": [], "why": "考试窗口内优先使用反馈密度更高的练习与错题", "success_evidence": ["复习地图", "答题记录", "错题重做记录"], "review_date": "考试前"}


class CompassEngine:
    def __init__(self, runtime_dir: str | Path | None = None) -> None:
        self.runtime = Path(runtime_dir or ROOT / "runtime")
        self.growth = GrowthOrchestrator(runtime_dir=self.runtime)

    def _paths(self, user_id: str) -> tuple[Path, Path, Path]:
        user_root = self.runtime / "users" / _safe_user_key(user_id)
        return user_root / "archive.json", user_root / "memory.sqlite3", user_root / "strategies"

    def run(self, request: Mapping[str, Any]) -> dict[str, Any]:
        user_id = str(request.get("user_id", "")).strip()
        if not user_id:
            raise ValueError("user_id 不能为空")
        message = str(request.get("message", "")).strip()
        attachments = list(request.get("attachments") or [])
        archive_path, memory_path, strategy_dir = self._paths(user_id)
        archive_exists = archive_path.exists()
        statuses: dict[str, str] = {}
        flow: list[str] = []

        # Safety always precedes identity, memory and planning.
        safety = route_safety(message)["data"]
        statuses["SAFETY"] = safety["type"]
        flow.append("safety_router")
        if safety["stop_learning_plan"]:
            response = {"current_judgment": "先暂停当前任务", "why": safety["response"], "do_now": ["联系身边可信任的人或合适的专业支持"], "next_step": "确认当下安全后再继续规划", "text": safety["response"]}
            return result(MODULE, {"intent": Intent.GENERAL_SUPPORT.value, "state": "SAFETY_ROUTED", "response": response, "text": response["text"], "trace": [{"step": "SAFETY", "status": safety["type"]}], "safety": safety, "archive": empty_archive(user_id)})

        archive = load_archive(archive_path, user_id=user_id)
        memory = MemoryEngine(memory_path)
        persistent_context = memory.load_user_context(user_id=user_id, query=message, top_k=5)
        recalled = memory.load(user_id=user_id, query=message, top_k=5)["data"]
        persistent_count = sum(bool(persistent_context.get(key)) for key in ("profile", "goal", "competency", "growth_state"))
        statuses["MEMORY_LOAD"] = f"{persistent_count}_structured_{recalled['count']}_records"
        flow.extend(["load_memory", "detect_new_or_returning_user"])

        intent = route_intent(message, attachments)
        statuses["INTENT"] = intent.value
        if intent is Intent.MEMORY_FORGET:
            forgotten = memory.forget(user_id=user_id)
            archive = empty_archive(user_id)
            save_archive(archive_path, archive)
            response = {"current_judgment": "已清空应用层长期记忆和成长档案", "why": "忘记请求优先于任何建档或规划", "do_now": [], "next_step": "需要时可以重新开始", "text": "已按你的要求清空应用层长期记忆和成长档案。需要时我们可以重新开始。"}
            statuses.update({"STATE": "MEMORY_REVIEW", "CONTEXT": "cleared", "BUSINESS": "forget", "MEMORY_WRITE": "hard_delete", "ARCHIVE": "saved_v22", "RESPONSE": "built"})
            return result(MODULE, {"intent": intent.value, "state": "MEMORY_REVIEW", "response": response, "text": response["text"], "trace": _trace(statuses), "safety": safety, "memory_change": forgotten, "archive": archive})

        incoming = extract_known_facts(message, request)
        facts = merge_known_facts(archive.get("known_facts"), incoming)
        archive["known_facts"] = facts
        archive["profile"].update(_profile_from_facts(facts))
        profile_updates = _profile_from_facts(facts)
        if profile_updates:
            profile_updates["preferred_name"] = fact_value(facts, "preferred_name", archive.get("preferred_name", ""))
            profile_updates["weekly_available_hours"] = profile_updates.get("weekly_hours", persistent_context.get("profile", {}).get("weekly_available_hours", 0))
            memory.persist_turn(user_id=user_id, profile_updates=profile_updates)
        if fact_value(incoming, "direction_status") == "changed":
            current_plan = dict(archive.get("academic", {}).get("current_plan") or {})
            if current_plan:
                current_plan.update({"status": "invalidated", "invalidated_reason": "user_changed_direction"})
                archive["academic"]["current_plan"] = current_plan
            confirmed_goal = dict(archive.get("career", {}).get("confirmed_goal") or {})
            if confirmed_goal:
                confirmed_goal.update({"status": "invalidated", "invalidated_reason": "user_changed_direction"})
                archive["career"]["confirmed_goal"] = confirmed_goal
        flow.extend(["preferred_name", "parse_current_message", "update_known_facts"])

        growth_cycle: dict[str, Any] | None = None
        target_city, target_job = fact_value(facts, "target_city", ""), fact_value(facts, "target_job", "")
        growth_operation = str(request.get("growth_operation", ""))
        if growth_operation in {"market", "gap", "plan", "full_cycle"} or request.get("jds") or request.get("public_urls") or (target_city and target_job) or intent in {Intent.RECRUITMENT_ANALYSIS, Intent.GAP_ANALYSIS, Intent.CAREER_GAP}:
            growth_request = {**dict(request), "target_city": request.get("target_city") or target_city, "target_job": request.get("target_job") or target_job, "job_search_time": request.get("job_search_time") or fact_value(facts, "deadline_time", ""), "message": message}
            growth_cycle = self.growth.market_learning_cycle(user_id=user_id, request=growth_request, archive=archive, memory=memory, context=persistent_context)
            archive.setdefault("extensions", {})["growth_cycle"] = growth_cycle
            persistent_context = memory.load_user_context(user_id=user_id, query=message, top_k=5)
            statuses["RESEARCH"] = growth_cycle["market"].get("market_data_status", "insufficient")

        onboarding = evaluate_onboarding(archive_exists=archive_exists, archive=archive, facts=facts, intent=intent.value)
        stage = onboarding["stage"]
        sufficiency = onboarding["sufficiency"]
        action = MentorAction(onboarding["action"])
        history = _question_history(archive)
        archive["preferred_name"] = str(onboarding["preferred_name"] or "")
        archive["preferred_name_usage"] = bool(onboarding["preferred_name_usage"])
        archive["current_growth_stage"] = stage["stage"]
        archive["profile_sufficiency"] = sufficiency
        archive["planning_confidence"] = sufficiency["confidence"]
        archive["last_action"] = action.value
        statuses.update({"STATE": onboarding["state"], "CONTEXT": "known_facts_built"})
        flow.extend(["detect_stage", "determine_intent", "calculate_profile_sufficiency", "duplicate_question_guard", "choose_action_or_question"])

        name = archive["preferred_name"]
        usage = bool(archive["preferred_name_usage"])
        memory_change = _write_explicit_facts(memory, user_id, incoming)
        statuses["MEMORY_WRITE"] = memory_change["action"]
        business: dict[str, Any] = {"action": action.value}
        questions: list[dict[str, Any]] = []

        if action is MentorAction.ASK_NAME:
            response = ask_name_response()
            _record_questions(history, ["preferred_name"], question_only=True)
            statuses["BUSINESS"] = "ask_name"
        elif "preferred_name" in incoming and not any(fact_value(facts, field) for field in ("major", "grade", "primary_need")):
            response = quick_profile_response(name, usage=usage)
            _record_questions(history, ["major", "grade", "primary_need"], question_only=True)
            statuses["BUSINESS"] = "quick_profile"
            archive["last_action"] = "ASK_MINIMUM_PROFILE"
            onboarding["state"] = "QUICK_PROFILE"
        elif not sufficiency["action_ready"]:
            fields = [*sufficiency["missing_blocking"], *sufficiency["missing_non_blocking"]]
            selection = select_questions(fields, facts, history["asked_fields"], question_only_streak=0, allow_non_blocking=False)
            questions = selection["questions"]
            if not questions:
                action = MentorAction.GIVE_STAGE_DIAGNOSIS
                sufficiency["action_ready"] = True
                business["action"] = action.value
            else:
                response = stage_question_response(name, stage, questions, usage=usage)
                _record_questions(history, selection["asked_fields"], question_only=False)
                statuses["BUSINESS"] = "stage_and_minimum_questions"

        tutor_ready = intent in {Intent.START_LEARNING, Intent.CONTINUE_LEARNING, Intent.SUBMIT_EXERCISE, Intent.SUBMIT_EVIDENCE} and bool(archive.get("academic", {}).get("current_plan", {}).get("weekly_core_tasks") or archive.get("extensions", {}).get("current_tutor"))
        if (sufficiency["action_ready"] or tutor_ready) and action not in {MentorAction.ASK_NAME, MentorAction.ASK_MINIMUM_PROFILE, MentorAction.ASK_BLOCKING_FIELD}:
            cold_start = not bool(archive.get("onboarding_complete"))
            daily = fact_value(facts, "daily_learning_hours")
            weekly = fact_value(facts, "weekly_learning_hours")
            exam_days = fact_value(facts, "exam_days")
            actual_history = list(archive.get("learning_strategy", {}).get("actual_hours_history") or [])
            if fact_value(incoming, "last_actual_hours") is not None:
                actual_history.append(float(fact_value(incoming, "last_actual_hours")))
                archive["learning_strategy"]["actual_hours_history"] = actual_history[-8:]
            completed_weeks = int(fact_value(facts, "completed_weeks", len(actual_history)) or 0)
            capacity = calculate_realistic_capacity(
                daily_hours=daily, weekly_hours=weekly, cold_start=cold_start and completed_weeks < 2,
                completed_weeks=completed_weeks, actual_hours=actual_history, exam_days=exam_days,
            )
            archive["realistic_capacity"] = capacity
            statuses["BUSINESS"] = action.value

            if intent in {Intent.START_LEARNING, Intent.CONTINUE_LEARNING}:
                tutor = self.growth.start_tutor(message=message, request=request, archive=archive, context=persistent_context, memory=memory, user_id=user_id, resume=intent is Intent.CONTINUE_LEARNING)
                business["tutor"] = tutor
                statuses["BUSINESS"] = tutor["action"]
                if tutor.get("status") == "no_task":
                    text = str(tutor["message"])
                else:
                    lesson = tutor.get("lesson", {})
                    exercise = tutor.get("exercise", {})
                    text = f"现在进入 {tutor.get('skill', '当前能力')} 的陪学环节，不重新生成计划。\n{lesson.get('explanation', '')}\n{lesson.get('example', '')}\n练习：{exercise.get('prompt', '继续当前练习')}"
                response = {"current_judgment": "进入 AI Tutor", "why": "当前输入是开始或继续学习，不是重新规划", "do_now": [tutor.get("exercise", {}).get("prompt", "继续当前学习")], "next_step": tutor.get("next_action", "继续学习"), "mentor_sections": {"tutor": tutor}, "text": text}
            elif intent in {Intent.SUBMIT_EXERCISE, Intent.SUBMIT_EVIDENCE}:
                assessed = self.growth.assess(request=request, archive=archive, context=persistent_context, memory=memory, user_id=user_id)
                business["assessment"] = assessed
                statuses["BUSINESS"] = "ASSESS_LEARNING"
                text = assessed.get("assessment", {}).get("feedback", "当前没有可验收的活动练习。")
                if assessed.get("replanned"):
                    text += " 已形成能力证据、更新 Competency，并据此重新计算 Gap 与计划。"
                response = {"current_judgment": "学习成果已验收" if assessed.get("assessment") else "暂无活动练习", "why": "只有通过可观察验收的结果才会更新已验证能力", "do_now": [], "next_step": "继续下一项计划任务" if assessed.get("replanned") else "补齐未通过的验收项", "mentor_sections": {"assessment": assessed}, "text": text}
            elif growth_cycle is not None:
                business["growth_cycle"] = growth_cycle
                market, plan = growth_cycle["market"], growth_cycle["plan"]
                tasks = plan.get("weekly_core_tasks", [])
                if tasks:
                    text = f"已按 {market.get('target_city')} {market.get('target_job_normalized')} 的可追溯样本完成市场→Gap→计划计算。\n{tasks[0]['why']}\n本周先做：{tasks[0]['title']}"
                else:
                    text = f"已生成动态招聘查询，但当前市场数据状态为 {market.get('market_data_status', 'insufficient')}。没有足够真实样本时，我不会虚构岗位比例；你可以提供公开招聘链接或完整 JD。"
                response = {"current_judgment": "已完成市场驱动分析" if tasks else "招聘样本暂时不足", "why": plan.get("notice", ""), "do_now": [item.get("title", "") for item in tasks[:3]], "next_step": "开始第一项 Tutor 任务" if tasks else "补充公开来源或用户 JD", "mentor_sections": {"market_driven_learning": growth_cycle}, "text": text}
            elif intent is Intent.STRATEGY_FEEDBACK:
                improvement = ImprovementEngine(strategy_dir).observe(
                    user_id=user_id, task_id=str(request.get("task_id", "current-turn")), category="plan_feedback",
                    signal=str(request.get("signal", "plan.overload" if "太多" in message else message)), context={"stage": stage["stage"]},
                )
                capacity["planned_weekly_hours"] = round(float(capacity["planned_weekly_hours"]) * 0.75, 2)
                archive["realistic_capacity"] = capacity
                current = archive.get("academic", {}).get("current_plan") or {}
                tasks = list(current.get("weekly_core_tasks") or [])[:2]
                text = f"{name + '，' if name and usage else ''}这周先降载，不需要硬撑原计划。先保留最多 2 个核心任务，周上限调整为约 {capacity['planned_weekly_hours']:g} 小时。下次告诉我实际用了多久和主要卡点，我会继续校准。"
                response = {"current_judgment": "当前计划负荷偏高", "why": "你的明确反馈优先于原计划", "do_now": [task.get("title", "") for task in tasks] or ["保留一个最重要任务"], "next_step": "反馈实际用时和卡点", "mentor_sections": {"load_adjustment": text}, "text": text}
                business["improvement"] = improvement
                statuses["IMPROVEMENT"] = "observed"
                if improvement.get("suggestion"):
                    suggestion = improvement["suggestion"]
                    evolver = EvolutionEngine(strategy_dir / "evolution", acceptance_improvement_threshold=0.05)
                    candidate = evolver.propose(gene="feedback_adaptation", capsule={"change": suggestion["change"], "requires_trial": True}, evidence=[str(suggestion["pattern_key"])])
                    trial = evolver.start_trial(candidate["strategy_id"], metric="completion_rate", baseline=float(persistent_context.get("growth_state", {}).get("completion_rate", 0.0)))
                    business["evolution_candidate"] = candidate
                    business["evolution_trial"] = trial
                    statuses["EVOLUTION"] = "trial_started"
            elif action is MentorAction.RUN_PROGRESS_REVIEW:
                response = _progress_response(name, archive, usage)
                business["recalled"] = recalled
            elif action is MentorAction.RUN_REVIEW:
                paths = [item.get("path") if isinstance(item, dict) else item for item in attachments]
                valid_paths = [str(path) for path in paths if path]
                review = ReviewEngine().build(course=str(fact_value(facts, "course", request.get("course", "未命名课程"))), material_paths=valid_paths) if valid_paths else {"knowledge_points": [], "questions": [], "answers": [], "warnings": ["未提供课程材料，当前为基础复习策略，不代表教师真实考点"]}
                archive["exam"]["knowledge_points"] = review.get("knowledge_points", [])
                goal_plan = _exam_plan(str(fact_value(facts, "course", request.get("course", ""))), valid_paths, int(exam_days) if exam_days is not None else None)
                diagnosis = build_mentor_diagnosis(facts, stage, planning_confidence=sufficiency["confidence"])
                response = action_response(name, diagnosis, goal_plan, capacity, usage=usage)
                business.update({"review": review, "goal_plan": goal_plan})
                archive["academic"]["current_plan"] = goal_plan
                statuses["REVIEW"] = "priority"
            elif intent is Intent.RESOURCE_SEARCH:
                url = str(request.get("url", "")).strip()
                if url:
                    host = urlparse(url).hostname or ""
                    research = ResearchEngine(project_root=ROOT, allowed_domains={host.casefold()}).read_page(url, selector=str(request.get("selector", "body")))
                    text = (f"{name + '，' if name and usage else ''}已按公共网页只读策略读取资料，请先核对来源、日期和课程适配性。" if research["ok"] else f"{name + '，' if name and usage else ''}公开网页读取失败，当前已安全降级；可以上传本地材料或使用版本化快照。")
                    response = {"current_judgment": "资料已读取" if research["ok"] else "资料读取已降级", "why": "仅访问明确提供的公共 HTTPS 来源", "do_now": ["核对来源和适配性"], "next_step": "确认后加入学习任务", "mentor_sections": {"research": text}, "text": text}
                    business["research"] = research
                    business.update(research)
                    statuses["RESEARCH"] = research["mode"]
                else:
                    text = f"{name + '，' if name and usage else ''}我可以帮你判断资料，但不会在没有授权目标时自行浏览。先给出一个公共 HTTPS 地址；这不影响你继续执行现有计划。"
                    response = {"current_judgment": "需要明确的公开来源", "why": "Research Brain 默认只读且有界", "do_now": [], "next_step": "提供 URL 或本地材料", "mentor_sections": {"research": text}, "text": text}
                    business["research"] = {"ok": False, "mode": "explicit-url-required"}
                    business.update(business["research"])
                    statuses["RESEARCH"] = "explicit-url-required"
            elif action is MentorAction.EXPLORE_CAREER:
                features = extract_features(archive["profile"], message)
                directions = _prioritize_directions(analyze_directions(features), facts)
                selection = select_questions(["confirmed_direction", "daily_learning_hours"], facts, history["asked_fields"], question_only_streak=0)
                questions = selection["questions"]
                _record_questions(history, selection["asked_fields"], question_only=False)
                response = _career_explore_response(name, usage, stage, directions, questions)
                business.update({"features": features.to_dict(), "directions": directions, "notice": "适配分只用于方向比较，不是就业概率或人格测评。"})
                archive["career"]["directions"] = directions
            else:
                diagnosis = build_mentor_diagnosis(facts, stage, planning_confidence=sufficiency["confidence"])
                goal_plan = build_goal_plan(facts, stage, capacity, planning_mode=sufficiency["planning_mode"])
                later = select_questions(["target_city"], facts, history["asked_fields"], question_only_streak=0)["questions"]
                _record_questions(history, [item["field"] for item in later], question_only=False)
                directions: list[dict[str, Any]] = []
                if fact_value(facts, "career_direction"):
                    directions = _prioritize_directions(analyze_directions(extract_features(archive["profile"], message)), facts)
                    archive["career"]["directions"] = directions
                response = action_response(name, diagnosis, goal_plan, capacity, directions=directions, later_questions=later, usage=usage)
                business.update({"diagnosis": diagnosis, "goal_plan": goal_plan, "capacity": capacity, "directions": directions})
                archive["academic"]["current_plan"] = goal_plan
                if fact_value(facts, "direction_status") == "confirmed":
                    archive["career"]["confirmed_goal"] = {"primary_direction": fact_value(facts, "career_direction"), "target_city": fact_value(facts, "target_city", ""), "timeline": fact_value(facts, "deadline_time", ""), "status": "confirmed"}
                archive["onboarding_complete"] = True
                archive["next_expected_update"] = ["tasks_completed", "actual_hours", "main_blocker"]
            _record_questions(history, [], question_only=False)

        archive["question_history"] = history
        archive["memory_change_summary"] = memory_change
        archive["profile_sufficiency"] = sufficiency
        archive["last_action"] = business.get("action", archive.get("last_action", ""))
        persistent_write = memory.persist_turn(
            user_id=user_id,
            profile_updates={**archive.get("profile", {}), "preferred_name": archive.get("preferred_name", "")},
            goal_updates=archive.get("career", {}).get("confirmed_goal", {}),
            growth_updates={
                "current_stage": archive.get("current_growth_stage", ""),
                "current_plan": archive.get("academic", {}).get("current_plan", {}),
                "active_tasks": archive.get("academic", {}).get("current_plan", {}).get("weekly_core_tasks", []),
                **({"current_lesson": archive.get("extensions", {}).get("current_tutor", {}).get("lesson", {})} if archive.get("extensions", {}).get("current_tutor") else {}),
            },
        )
        business["persistent_memory"] = {"stored": persistent_write.get("stored", False), "health": memory.health()}
        proactive_history = list(archive.setdefault("extensions", {}).get("proactive_feedback", []))
        last_prompt = dict(archive["extensions"].get("last_proactive_prompt", {}))
        progress = {**persistent_context.get("growth_state", {}), **dict(request.get("progress_signals") or {})}
        market_state = archive.get("career", {}).get("recruitment_snapshot", {})
        previous_goal = persistent_context.get("goal", {})
        target_changed = any(
            bool(previous_goal.get("target_city" if key == "target_city" else "target_job_raw") or previous_goal.get("target_job_normalized" if key == "target_job" else ""))
            and fact_value(incoming, key) != (previous_goal.get("target_city") if key == "target_city" else previous_goal.get("target_job_raw") or previous_goal.get("target_job_normalized"))
            for key in ("target_city", "target_job") if key in incoming
        )
        proactive_signals = {
            "exam_days": fact_value(facts, "exam_days"), "missed_tasks": request.get("missed_tasks", progress.get("missed_tasks", 0)),
            "stress": request.get("stress", 0), "completion_rate": request.get("completion_rate", progress.get("completion_rate")),
            "actual_hours_ratio": request.get("actual_hours_ratio", progress.get("actual_hours_ratio")), "job_search_days": request.get("job_search_days"),
            "target_changed": target_changed, "market_snapshot_stale": request.get("market_snapshot_stale", market_state.get("stale", False)),
            "gap_stalled_weeks": request.get("gap_stalled_weeks", progress.get("gap_stalled_weeks", 0)),
            "weeks_without_evidence": request.get("weeks_without_evidence", progress.get("weeks_without_evidence", 0)),
        }
        proactive_engine = ProactiveEngine()
        proactive = proactive_engine.check(signals=proactive_signals, last_prompt_at=str(last_prompt.get("prompted_at", "")), feedback_history=proactive_history)
        feedback_value = str(request.get("proactive_feedback", ""))
        if feedback_value:
            prompt_for_feedback = last_prompt or proactive
            feedback = proactive_engine.feedback(prompt_for_feedback, feedback_value)
            proactive_history.append(feedback)
            archive["extensions"]["proactive_feedback"] = proactive_history[-20:]
            business["proactive_feedback"] = feedback
            if feedback_value == "rejected":
                business["proactive_improvement"] = ImprovementEngine(strategy_dir).observe_event(event_type="correction", pattern_key=f"proactive.false-positive.{feedback.get('reason', 'unknown')}", summary="主动建议被用户拒绝，需要降低同类触发频率", area="proactive", user_id=user_id, task_id=str(request.get("turn_id", "current-turn")))
        if proactive.get("should_prompt"):
            archive["extensions"]["last_proactive_prompt"] = proactive
            response["text"] = f"{response['text']}\n\n主动建议：{proactive['message']}"
            response.setdefault("mentor_sections", {})["proactive_suggestion"] = proactive["message"]
        business["proactive"] = proactive
        statuses["PROACTIVE"] = "prompt" if proactive["should_prompt"] else proactive["reason"]
        statuses.setdefault("REVIEW", "quality_checked")
        statuses.setdefault("RESEARCH", "not_requested")
        statuses.setdefault("IMPROVEMENT", "not_triggered")
        statuses.setdefault("EVOLUTION", "not_triggered")
        statuses["ARCHIVE"] = "saved_v22"
        statuses["RESPONSE"] = "built"
        flow.extend(["execute_business_engine", "mentor_diagnosis", "goal_planning", "weekly_capacity", "plan_generation", "improvement", "evolution", "proactive", "memory_write", "archive_update", "mentor_response"])
        save_archive(archive_path, archive)

        if request.get("debug"):
            write_interaction_trace(self.runtime, {"state": onboarding["state"], "known_facts": facts, "missing_fields": sufficiency["missing_blocking"], "sufficiency": sufficiency, "action_selected": business.get("action"), "questions_asked": [item.get("field") for item in questions]})
        details = {"business": business, "proactive": proactive}
        response.setdefault("details", details)
        response["details"] = details
        return result(MODULE, {
            "intent": intent.value, "state": onboarding["state"], "response": response, "text": response["text"],
            "trace": _trace(statuses), "safety": safety, "memory_change": memory_change, "archive": archive,
        })


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    runtime_dir = raw.get("runtime_dir") if isinstance(raw, Mapping) else None
    return CompassEngine(runtime_dir).run(raw)


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
