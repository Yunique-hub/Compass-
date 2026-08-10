"""Compass 2.5 correctness-first, domain-intelligent Growth Engine.

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

from scripts.academic.capacity_engine import allocate_weekly_capacity, calculate_realistic_capacity
from scripts.academic.major_engine import identify_academic_profile
from scripts.academic.pathway_engine import detect_pathway
from scripts.archive_v2 import empty_archive, load_archive, save_archive, synchronize_archive_states
from scripts.career.direction_engine import analyze as analyze_directions
from scripts.career.profile_engine import extract_features
from scripts.core.action_selector import MentorAction
from scripts.core.context_builder import build_context
from scripts.core.direct_answer import DirectAnswerHandler
from scripts.core.goal_planner import build_goal_plan
from scripts.core.growth_context import build_growth_context, pathway_options
from scripts.core.interaction_trace import write_interaction_trace
from scripts.core.intent_router import Intent, route_intent
from scripts.core.known_facts import extract_known_facts, fact_value, merge_known_facts
from scripts.core.mentor_diagnosis import build_mentor_diagnosis
from scripts.core.mentor_response_builder import action_response, ask_name_response, quick_profile_response, stage_question_response
from scripts.core.onboarding_engine import evaluate_onboarding
from scripts.core.question_policy import select_questions
from scripts.core.response_builder import build_response, normalize_response
from scripts.core.turn_context import TurnContext
from scripts.core.understanding import understand_message
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
TURN_PIPELINE = ["SAFETY", "RESTORE", "UNDERSTAND", "DECIDE", "EXECUTE", "LEARN", "PERSIST", "RESPOND"]


def _safe_user_key(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()[:24]


def _trace(statuses: Mapping[str, str]) -> list[dict[str, str]]:
    phase_status = {
        "SAFETY": statuses.get("SAFETY", "normal"),
        "RESTORE": statuses.get("MEMORY_LOAD", "restored"),
        "UNDERSTAND": statuses.get("CONTEXT", statuses.get("INTENT", "understood")),
        "DECIDE": statuses.get("STATE", "decided"),
        "EXECUTE": statuses.get("BUSINESS", "completed"),
        "LEARN": statuses.get("MEMORY_WRITE", "no_change"),
        "PERSIST": statuses.get("ARCHIVE", "saved"),
        "RESPOND": statuses.get("RESPONSE", "built"),
    }
    return [{"step": step, "status": str(phase_status[step])} for step in TURN_PIPELINE]


def _profile_from_facts(facts: Mapping[str, Any]) -> dict[str, Any]:
    profile: dict[str, Any] = {}
    for key in ("preferred_name", "education_level", "grade", "major", "secondary_major", "minor", "primary_need", "daily_learning_hours", "weekly_learning_hours", "company_preference"):
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


def _profile_sources(facts: Mapping[str, Any]) -> dict[str, str]:
    return {
        key: str(item.get("source", ""))
        for key, item in facts.items()
        if isinstance(item, Mapping)
    }


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
        "content": {"key": key, "value": item.get("value"), "certainty": "known", "user_explicit": True, "confirmed": True},
        "importance": importance, "stability": 0.9, "future_relevance": 0.9,
        "user_explicitness": 1.0, "recurrence": 0.5, "confidence": float(item.get("confidence", 1.0)),
        "task_value": 0.9, "user_intent": "",
    }


def _write_explicit_facts(memory: MemoryEngine, user_id: str, incoming: Mapping[str, Any]) -> dict[str, Any]:
    changes = []
    for key, item in incoming.items():
        if item.get("source") != "user_explicit" or float(item.get("confidence", 0.0)) < 1.0:
            changes.append({"key": key, "stored": False, "action": "inference_not_persisted"})
            continue
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


def _pathway_explore_response(name: str, usage: bool, stage: Mapping[str, Any], options: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    prefix = f"{name}，" if name and usage else ""
    lines = [
        f"{prefix}当前更适合做成长路径探索，不需要马上把专业等同于唯一职业。",
        f"结合{stage.get('label', '当前阶段')}与学科能力基础，可以比较以下方向：",
    ]
    lines.extend(f"{index}. {item['title']}：{item['why']}；先验证：{item['experiment']}" for index, item in enumerate(options, 1))
    lines.append("先完成两个低成本体验，再用兴趣、完成质量和现实约束比较，不强行锁定方向。")
    text = "\n".join(lines)
    return build_response(
        "当前处于方向探索阶段",
        "专业提供可迁移的能力基础，但不直接等于职业结论",
        [item["experiment"] for item in options[:2]],
        "完成体验后比较证据并缩小到 1–2 条路径",
        goal="用真实体验验证成长路径",
        text=text,
        details={"pathway_options": list(options)},
    ) | {"mentor_sections": {"pathway_options": list(options)}}


def _exam_plan(course: str, materials: list[str], exam_days: int | None) -> dict[str, Any]:
    tasks = [
        {"title": "列出考试知识点优先级", "why": "先确定有限时间内的覆盖顺序", "estimated_time": 2, "specific_action": ["按章节列知识点", "标记真题和教师强调", "选出前三个薄弱点"], "output": ["review-map.md"], "acceptance_criteria": ["至少列出 10 个知识点并标优先级"], "evidence": "复习地图", "fallback": "无材料时按课程目录建立临时版本"},
        {"title": "完成一轮限时练习", "why": "用答题结果代替重复阅读", "estimated_time": 3, "specific_action": ["完成一组题", "独立作答", "核对并标错因"], "output": ["答题记录"], "acceptance_criteria": ["每道错题有知识点和错因"], "evidence": "答案与批改", "fallback": "没有题库时先做课后题"},
        {"title": "重做最高频错题", "why": "把反馈转成可验证掌握度", "estimated_time": 2, "specific_action": ["隔开答案重做", "口头解释关键步骤"], "output": ["错题重做记录"], "acceptance_criteria": ["重做正确并能解释"], "evidence": "重做结果", "fallback": "先重做最重要的 3 道"},
    ]
    return {"plan_type": "REVIEW_PLAN", "primary_goal": f"在{f'未来 {exam_days} 天' if exam_days is not None else '当前复习周期'}完成{course or '这门课'}的重点覆盖、练习反馈和错题重做", "goal_horizon": f"{exam_days} 天" if exam_days is not None else "本周", "stage_goals": [{"period": "现在", "goal": "重点识别"}, {"period": "中段", "goal": "限时练习"}, {"period": "考前", "goal": "错题重做"}], "current_stage_goal": "先完成复习地图", "week_goal": "完成重点、练习和错题闭环", "weekly_core_tasks": tasks, "optional_tasks": [], "why": "考试窗口内优先使用反馈密度更高的练习与错题", "success_evidence": ["复习地图", "答题记录", "错题重做记录"], "review_date": "考试前"}


def _knowledge_response(message: str, handler: DirectAnswerHandler) -> dict[str, Any]:
    text = handler.answer(message)
    return build_response("直接回答当前知识问题", "简单问题不需要启动完整成长规划", next_step="需要时给一个最小示例", text=text)


class CompassEngine:
    def __init__(self, runtime_dir: str | Path | None = None) -> None:
        self.runtime = Path(runtime_dir or ROOT / "runtime")
        self.growth = GrowthOrchestrator(runtime_dir=self.runtime)
        self.direct_answer = DirectAnswerHandler()

    def _paths(self, user_id: str) -> tuple[Path, Path, Path]:
        user_root = self.runtime / "users" / _safe_user_key(user_id)
        return user_root / "archive.json", user_root / "memory.sqlite3", user_root / "strategies"

    def run(self, request: Mapping[str, Any]) -> dict[str, Any]:
        user_id = str(request.get("user_id", "")).strip()
        paths = self._paths(user_id) if user_id else (Path(), Path(), Path())
        turn = TurnContext.create(request, archive_path=paths[0], memory_path=paths[1], strategy_dir=paths[2])
        early = self._check_safety(turn) or self._restore_and_understand(turn)
        if early:
            return early
        self._execute(turn)
        return self._persist_and_respond(turn)

    def _check_safety(self, turn: TurnContext) -> dict[str, Any] | None:
        turn.safety = route_safety(turn.message)["data"]
        turn.statuses["SAFETY"] = turn.safety["type"]
        turn.flow.append("safety_router")
        if not turn.safety["stop_learning_plan"]:
            return None
        turn.response = build_response(
            "先暂停当前任务", turn.safety["response"], ["联系身边可信任的人或合适的专业支持"],
            "确认当下安全后再继续规划", text=turn.safety["response"],
        )
        return result(MODULE, {"intent": Intent.GENERAL_SUPPORT.value, "state": "SAFETY_ROUTED", "response": turn.response, "text": turn.response["text"], "trace": [{"step": "SAFETY", "status": turn.safety["type"]}], "safety": turn.safety, "archive": empty_archive(turn.user_id)})

    def _restore_and_understand(self, turn: TurnContext) -> dict[str, Any] | None:
        turn.archive = load_archive(turn.archive_path, user_id=turn.user_id)
        turn.memory = MemoryEngine(turn.memory_path)
        turn.persistent_context = turn.memory.load_user_context(user_id=turn.user_id, query=turn.message, top_k=5)
        turn.recalled = turn.memory.load(user_id=turn.user_id, query=turn.message, top_k=5)["data"]
        persistent_count = sum(bool(turn.persistent_context.get(key)) for key in ("profile", "goal", "competency", "growth_state"))
        turn.statuses["MEMORY_LOAD"] = f"{persistent_count}_structured_{turn.recalled['count']}_records"
        active_exercise = bool(turn.archive.get("extensions", {}).get("current_tutor", {}).get("exercise"))
        turn.understanding = understand_message(turn.message, turn.attachments, active_exercise=active_exercise)
        turn.intent = Intent(turn.understanding.primary_intent)
        turn.statuses["INTENT"] = turn.intent.value
        if turn.intent is Intent.MEMORY_FORGET:
            return self._forget(turn)

        turn.incoming = extract_known_facts(turn.message, turn.request)
        turn.facts = merge_known_facts(turn.archive.get("known_facts"), turn.incoming)
        turn.archive["known_facts"] = turn.facts
        turn.archive["profile"].update(_profile_from_facts(turn.facts))
        profile_updates = _profile_from_facts(turn.facts)
        if profile_updates:
            profile_updates["preferred_name"] = fact_value(turn.facts, "preferred_name", turn.archive.get("preferred_name", ""))
            profile_updates["weekly_available_hours"] = profile_updates.get("weekly_hours", turn.persistent_context.get("profile", {}).get("weekly_available_hours", 0))
            turn.memory.persist_turn(user_id=turn.user_id, profile_updates=profile_updates, profile_sources=_profile_sources(turn.facts))
        self._invalidate_changed_direction(turn)
        self._maybe_run_market_cycle(turn)

        turn.onboarding = evaluate_onboarding(archive_exists=turn.archive_exists, archive=turn.archive, facts=turn.facts, intent=turn.intent.value)
        turn.stage = turn.onboarding["stage"]
        turn.sufficiency = turn.onboarding["sufficiency"]
        previous_academic = turn.archive.get("profile", {}).get("academic_profile") or {}
        turn.academic_profile = identify_academic_profile(turn.message, previous_academic)
        turn.pathway = detect_pathway(turn.message, turn.facts, transition_target=turn.academic_profile.transition_target)
        daily = fact_value(turn.facts, "daily_learning_hours")
        weekly = fact_value(turn.facts, "weekly_learning_hours")
        weekly_capacity = float(weekly if weekly is not None else (float(daily) * 7 if daily is not None else 0))
        turn.growth_context = build_growth_context(
            turn.academic_profile,
            turn.pathway,
            stage=str(turn.stage.get("stage", "")),
            weekly_capacity=weekly_capacity,
            constraints={"exam_days": fact_value(turn.facts, "exam_days"), "target_city": fact_value(turn.facts, "target_city", "")},
        )
        turn.archive["profile"]["academic_profile"] = turn.academic_profile.to_dict()
        turn.archive.setdefault("extensions", {})["growth_context"] = turn.growth_context.to_dict()
        turn.action = MentorAction(turn.onboarding["action"])
        turn.history = _question_history(turn.archive)
        turn.archive.update({
            "preferred_name": str(turn.onboarding["preferred_name"] or ""),
            "preferred_name_usage": bool(turn.onboarding["preferred_name_usage"]),
            "current_growth_stage": turn.stage["stage"],
            "profile_sufficiency": turn.sufficiency,
            "planning_confidence": turn.sufficiency["confidence"],
            "last_action": turn.action.value,
        })
        turn.memory_change = _write_explicit_facts(turn.memory, turn.user_id, turn.incoming)
        turn.statuses.update({"STATE": turn.onboarding["state"], "CONTEXT": "known_facts_built", "MEMORY_WRITE": turn.memory_change["action"]})
        return None

    def _forget(self, turn: TurnContext) -> dict[str, Any]:
        forgotten = turn.memory.forget(user_id=turn.user_id)
        turn.archive = synchronize_archive_states(empty_archive(turn.user_id))
        save_archive(turn.archive_path, turn.archive)
        turn.response = build_response("已清空应用层长期记忆和成长档案", "忘记请求优先于任何建档或规划", next_step="需要时可以重新开始", text="已按你的要求清空应用层长期记忆和成长档案。需要时我们可以重新开始。")
        turn.statuses.update({"STATE": "MEMORY_REVIEW", "CONTEXT": "cleared", "BUSINESS": "forget", "MEMORY_WRITE": "hard_delete", "ARCHIVE": "saved_v25", "RESPONSE": "built"})
        return result(MODULE, {"intent": turn.intent.value, "state": "MEMORY_REVIEW", "response": turn.response, "text": turn.response["text"], "trace": _trace(turn.statuses), "safety": turn.safety, "memory_change": forgotten, "archive": turn.archive})

    @staticmethod
    def _invalidate_changed_direction(turn: TurnContext) -> None:
        if fact_value(turn.incoming, "direction_status") != "changed":
            return
        for section, key in (("academic", "current_plan"), ("career", "confirmed_goal")):
            current = dict(turn.archive.get(section, {}).get(key) or {})
            if current:
                current.update({"status": "invalidated", "invalidated_reason": "user_changed_direction"})
                turn.archive[section][key] = current

    def _maybe_run_market_cycle(self, turn: TurnContext) -> None:
        target_city = fact_value(turn.facts, "target_city", "")
        target_job = fact_value(turn.facts, "target_job", "")
        operation = str(turn.request.get("growth_operation", ""))
        requested = operation in {"market", "gap", "plan", "full_cycle"} or turn.request.get("jds") or turn.request.get("public_urls") or turn.intent in {Intent.RECRUITMENT_ANALYSIS, Intent.GAP_ANALYSIS, Intent.CAREER_GAP}
        if not requested:
            return
        growth_request = {**dict(turn.request), "target_city": turn.request.get("target_city") or target_city, "target_job": turn.request.get("target_job") or target_job, "job_search_time": turn.request.get("job_search_time") or fact_value(turn.facts, "deadline_time", ""), "message": turn.message}
        turn.growth_cycle = self.growth.market_learning_cycle(user_id=turn.user_id, request=growth_request, archive=turn.archive, memory=turn.memory, context=turn.persistent_context)
        turn.archive.setdefault("extensions", {})["growth_cycle"] = turn.growth_cycle
        turn.persistent_context = turn.memory.load_user_context(user_id=turn.user_id, query=turn.message, top_k=5)
        turn.statuses["RESEARCH"] = turn.growth_cycle["market"].get("market_data_status", "insufficient")

    def _execute(self, turn: TurnContext) -> None:
        name = turn.archive["preferred_name"]
        usage = bool(turn.archive["preferred_name_usage"])
        turn.business = {"action": turn.action.value, "understanding": turn.understanding.to_dict(), "growth_context": turn.growth_context.to_dict()}
        if turn.safety.get("type") == "stress":
            capacity = self._calculate_capacity(turn)
            plan = dict(turn.archive.get("academic", {}).get("current_plan") or {})
            tasks = list(plan.get("weekly_core_tasks") or [])[:1]
            if tasks:
                task = dict(tasks[0])
                if capacity.get("planned_weekly_hours"):
                    task["estimated_time"] = min(float(task.get("estimated_time", 0.0)), float(capacity["planned_weekly_hours"]))
                tasks = [task]
                plan["weekly_core_tasks"] = tasks
                plan["load_adjusted"] = True
                plan["load_adjustment_reason"] = "current_stress"
                turn.archive["academic"]["current_plan"] = plan
            actions = [task.get("title", "") for task in tasks] or ["暂停新增任务，只保留休息和一项最小恢复动作"]
            turn.response = build_response(
                "本周先降载", "当前压力反馈优先于原计划", actions, "状态缓解后再按实际精力恢复任务",
                goal="恢复可持续节奏", text=f"{turn.safety['response']} 本周实际计划上限已调整为约 {capacity.get('planned_weekly_hours', 0):g} 小时。",
            )
            turn.business["action"] = "STRESS_LOAD_ADJUSTMENT"
            turn.business["capacity"] = capacity
            turn.statuses["BUSINESS"] = "stress_load_adjusted"
            return
        tutor_ready = turn.intent is Intent.START_LEARNING or (
            turn.intent in {Intent.CONTINUE_LEARNING, Intent.SUBMIT_EXERCISE, Intent.SUBMIT_EVIDENCE}
            and bool(turn.archive.get("academic", {}).get("current_plan", {}).get("weekly_core_tasks") or turn.archive.get("extensions", {}).get("current_tutor"))
        )
        if turn.action is MentorAction.ASK_NAME:
            turn.response = ask_name_response()
            _record_questions(turn.history, ["preferred_name"], question_only=True)
            turn.statuses["BUSINESS"] = "ask_name"
            return
        if turn.action is MentorAction.ANSWER_KNOWLEDGE:
            turn.response = _knowledge_response(turn.message, self.direct_answer)
            turn.statuses["BUSINESS"] = "knowledge_answer"
            return
        if "preferred_name" in turn.incoming and not any(fact_value(turn.facts, field) for field in ("major", "grade", "primary_need")):
            turn.response = quick_profile_response(name, usage=usage)
            _record_questions(turn.history, ["major"], question_only=True)
            turn.archive["last_action"] = "ASK_MINIMUM_PROFILE"
            turn.onboarding["state"] = "QUICK_PROFILE"
            turn.statuses["BUSINESS"] = "quick_profile"
            return
        if not turn.sufficiency["action_ready"] and not tutor_ready:
            fields = [*turn.sufficiency["missing_blocking"], *turn.sufficiency["missing_non_blocking"]]
            selection = select_questions(fields, turn.facts, turn.history["asked_fields"], question_only_streak=0, allow_non_blocking=False)
            turn.questions = selection["questions"]
            if turn.questions:
                turn.response = stage_question_response(name, turn.stage, turn.questions, usage=usage)
                if turn.intent is Intent.RECRUITMENT_ANALYSIS:
                    turn.response["text"] += "\n当前没有足够可靠的实时招聘样本，市场结论仍需验证。"
                _record_questions(turn.history, selection["asked_fields"], question_only=False)
                turn.statuses["BUSINESS"] = "stage_and_minimum_questions"
                return
            turn.action = MentorAction.GIVE_STAGE_DIAGNOSIS
            turn.sufficiency["action_ready"] = True
            turn.business["action"] = turn.action.value

        if not turn.sufficiency["action_ready"] and not tutor_ready:
            return
        capacity = self._calculate_capacity(turn)
        turn.response = (
            self._handle_learning(turn)
            or self._handle_growth_cycle(turn)
            or self._handle_strategy_feedback(turn, capacity)
            or self._handle_review_or_resource(turn, capacity)
            or self._handle_career_or_plan(turn, capacity)
        )
        _record_questions(turn.history, [], question_only=False)

    @staticmethod
    def _calculate_capacity(turn: TurnContext) -> dict[str, Any]:
        actual_history = list(turn.archive.get("learning_strategy", {}).get("actual_hours_history") or [])
        if fact_value(turn.incoming, "last_actual_hours") is not None:
            actual_history.append(float(fact_value(turn.incoming, "last_actual_hours")))
            turn.archive["learning_strategy"]["actual_hours_history"] = actual_history[-8:]
        completed_weeks = int(fact_value(turn.facts, "completed_weeks", len(actual_history)) or 0)
        capacity = calculate_realistic_capacity(
            daily_hours=fact_value(turn.facts, "daily_learning_hours"), weekly_hours=fact_value(turn.facts, "weekly_learning_hours"),
            cold_start=not bool(turn.archive.get("onboarding_complete")) and completed_weeks < 2,
            completed_weeks=completed_weeks, actual_hours=actual_history, exam_days=fact_value(turn.facts, "exam_days"),
        )
        load_factor = max(0.0, min(1.0, float(turn.safety.get("task_load_factor", 1.0))))
        if load_factor < 1.0:
            capacity["planned_weekly_hours"] = round(float(capacity["planned_weekly_hours"]) * load_factor, 2)
            capacity["initial_load_ratio"] = round(float(capacity["initial_load_ratio"]) * load_factor, 3)
            capacity["allocation"] = allocate_weekly_capacity(capacity["planned_weekly_hours"], exam_days=fact_value(turn.facts, "exam_days"))
            capacity["safety_load_factor"] = load_factor
        turn.archive["realistic_capacity"] = capacity
        turn.statuses["BUSINESS"] = turn.action.value
        return capacity

    def _handle_learning(self, turn: TurnContext) -> dict[str, Any] | None:
        if turn.intent in {Intent.START_LEARNING, Intent.CONTINUE_LEARNING}:
            learning_request = dict(turn.request)
            if not learning_request.get("skill") and turn.understanding.current_topic:
                learning_request["skill"] = turn.understanding.current_topic
            tutor = self.growth.start_tutor(message=turn.message, request=learning_request, archive=turn.archive, context=turn.persistent_context, memory=turn.memory, user_id=turn.user_id, resume=turn.intent is Intent.CONTINUE_LEARNING)
            turn.business["tutor"] = tutor
            turn.statuses["BUSINESS"] = tutor["action"]
            if tutor.get("status") == "no_task":
                text = str(tutor["message"])
            else:
                lesson, exercise = tutor.get("lesson", {}), tutor.get("exercise", {})
                text = f"现在进入 {tutor.get('skill', '当前能力')} 的陪学环节，不重新生成计划。\n{lesson.get('explanation', '')}\n{lesson.get('example', '')}\n练习：{exercise.get('prompt', '继续当前练习')}"
            return build_response("进入 AI Tutor", "当前输入是开始或继续学习，不是重新规划", [tutor.get("exercise", {}).get("prompt", "继续当前学习")], tutor.get("next_action", "继续学习"), goal=str(tutor.get("skill", "完成当前学习任务")), text=text, details={"tutor": tutor}) | {"mentor_sections": {"tutor": tutor}}
        if turn.intent not in {Intent.SUBMIT_EXERCISE, Intent.SUBMIT_EVIDENCE}:
            return None
        assessed = self.growth.assess(request=turn.request, archive=turn.archive, context=turn.persistent_context, memory=turn.memory, user_id=turn.user_id)
        turn.business["assessment"] = assessed
        turn.statuses["BUSINESS"] = "ASSESS_LEARNING"
        text = assessed.get("assessment", {}).get("feedback", "当前没有可验收的活动练习。")
        if assessed.get("replanned"):
            text += " 已形成能力证据、更新 Competency，并据此重新计算 Gap 与计划。"
        return build_response("学习成果已验收" if assessed.get("assessment") else "暂无活动练习", "只有通过可观察验收的结果才会更新已验证能力", next_step="继续下一项计划任务" if assessed.get("replanned") else "补齐未通过的验收项", text=text) | {"mentor_sections": {"assessment": assessed}}

    @staticmethod
    def _handle_growth_cycle(turn: TurnContext) -> dict[str, Any] | None:
        if turn.growth_cycle is None:
            return None
        turn.business["growth_cycle"] = turn.growth_cycle
        market, plan = turn.growth_cycle["market"], turn.growth_cycle["plan"]
        tasks = plan.get("weekly_core_tasks", [])
        if tasks:
            text = f"已按 {market.get('target_city')} {market.get('target_job_normalized')} 的可追溯样本完成市场→Gap→计划计算。\n{tasks[0]['why']}\n本周先做：{tasks[0]['title']}"
        else:
            text = f"已生成动态招聘查询，但当前市场数据状态为 {market.get('market_data_status', 'insufficient')}。真实样本不足，最新结论需验证；你可以提供公开招聘链接或完整 JD。"
        return build_response("已完成市场驱动分析" if tasks else "招聘样本暂时不足", plan.get("notice", ""), [item.get("title", "") for item in tasks[:3]], "开始第一项 Tutor 任务" if tasks else "补充公开来源或用户 JD", goal=str(plan.get("primary_goal", "对齐目标岗位")), text=text) | {"mentor_sections": {"market_driven_learning": turn.growth_cycle}}

    @staticmethod
    def _handle_strategy_feedback(turn: TurnContext, capacity: dict[str, Any]) -> dict[str, Any] | None:
        if turn.intent is not Intent.STRATEGY_FEEDBACK:
            return None
        improvement = ImprovementEngine(turn.strategy_dir).observe(user_id=turn.user_id, task_id=str(turn.request.get("task_id", "current-turn")), category="plan_feedback", signal=str(turn.request.get("signal", "plan.overload" if "太多" in turn.message else turn.message)), context={"stage": turn.stage["stage"]})
        capacity["planned_weekly_hours"] = round(float(capacity["planned_weekly_hours"]) * 0.75, 2)
        turn.archive["realistic_capacity"] = capacity
        tasks = list((turn.archive.get("academic", {}).get("current_plan") or {}).get("weekly_core_tasks") or [])[:2]
        name = turn.archive["preferred_name"] if turn.archive["preferred_name_usage"] else ""
        text = f"{name + '，' if name else ''}这周先降载，不需要硬撑原计划。先保留最多 2 个核心任务，周上限调整为约 {capacity['planned_weekly_hours']:g} 小时。下次告诉我实际用了多久和主要卡点，我会继续校准。"
        turn.business["improvement"] = improvement
        turn.statuses["IMPROVEMENT"] = "observed"
        if improvement.get("suggestion"):
            suggestion = improvement["suggestion"]
            evolver = EvolutionEngine(turn.strategy_dir / "evolution", acceptance_improvement_threshold=0.05)
            candidate = evolver.propose(gene="feedback_adaptation", capsule={"change": suggestion["change"], "requires_trial": True}, evidence=[str(suggestion["pattern_key"])])
            trial = evolver.start_trial(candidate["strategy_id"], metric="completion_rate", baseline=float(turn.persistent_context.get("growth_state", {}).get("completion_rate", 0.0)))
            turn.business.update({"evolution_candidate": candidate, "evolution_trial": trial})
            turn.statuses["EVOLUTION"] = "trial_started"
        return build_response("当前计划负荷偏高", "你的明确反馈优先于原计划", [task.get("title", "") for task in tasks] or ["保留一个最重要任务"], "反馈实际用时和卡点", goal="恢复可持续执行节奏", text=text) | {"mentor_sections": {"load_adjustment": text}}

    def _handle_review_or_resource(self, turn: TurnContext, capacity: dict[str, Any]) -> dict[str, Any] | None:
        name = turn.archive["preferred_name"] if turn.archive["preferred_name_usage"] else ""
        if turn.action is MentorAction.RUN_PROGRESS_REVIEW:
            turn.business["recalled"] = turn.recalled
            return _progress_response(name, turn.archive, bool(name))
        if turn.action is MentorAction.RUN_REVIEW:
            paths = [item.get("path") if isinstance(item, dict) else item for item in turn.attachments]
            valid_paths = [str(path) for path in paths if path]
            course = str(fact_value(turn.facts, "course", turn.request.get("course", "未命名课程")))
            review = ReviewEngine().build(course=course, material_paths=valid_paths) if valid_paths else {"knowledge_points": [], "questions": [], "answers": [], "warnings": ["未提供课程材料，当前为基础复习策略，不代表教师真实考点"]}
            turn.archive["exam"]["knowledge_points"] = review.get("knowledge_points", [])
            exam_days = fact_value(turn.facts, "exam_days")
            goal_plan = _exam_plan(course, valid_paths, int(exam_days) if exam_days is not None else None)
            diagnosis = build_mentor_diagnosis(turn.facts, turn.stage, planning_confidence=turn.sufficiency["confidence"])
            turn.business.update({"review": review, "goal_plan": goal_plan})
            turn.archive["academic"]["current_plan"] = goal_plan
            turn.statuses["REVIEW"] = "priority"
            return action_response(name, diagnosis, goal_plan, capacity, usage=bool(name))
        if turn.intent is not Intent.RESOURCE_SEARCH:
            return None
        url = str(turn.request.get("url", "")).strip()
        if url:
            host = urlparse(url).hostname or ""
            research = ResearchEngine(project_root=ROOT, allowed_domains={host.casefold()}).read_page(url, selector=str(turn.request.get("selector", "body")))
            text = f"{name + '，' if name else ''}{'已按公共网页只读策略读取资料，请核对来源、日期和适配性。' if research['ok'] else '公开网页读取失败，已安全降级；可上传本地材料或使用版本化快照。'}"
            judgment = "资料已读取" if research["ok"] else "资料读取已降级"
        else:
            research = {"ok": False, "mode": "explicit-url-required"}
            text = f"{name + '，' if name else ''}我不会在没有可靠来源时伪造实时结论。当前信息可能过期，最新情况需验证；请提供公共 HTTPS 地址、完整 JD 或带日期的快照。"
            judgment = "需要明确的公开来源"
        turn.business["research"] = research
        turn.business.update(research)
        turn.statuses["RESEARCH"] = research["mode"]
        turn.statuses["BUSINESS"] = "RESOURCE_SEARCH"
        return build_response(judgment, "Research 默认只读且有界", ["核对来源和适配性"] if research["ok"] else [], "确认后加入学习任务" if research["ok"] else "提供 URL 或本地材料", text=text) | {"mentor_sections": {"research": text}}

    def _handle_career_or_plan(self, turn: TurnContext, capacity: dict[str, Any]) -> dict[str, Any]:
        name = turn.archive["preferred_name"]
        usage = bool(turn.archive["preferred_name_usage"])
        if turn.action is MentorAction.EXPLORE_CAREER:
            if turn.academic_profile.discipline_family != "computer_information":
                options = pathway_options(turn.growth_context)
                turn.business["pathway_options"] = options
                turn.archive["career"]["pathway_options"] = options
                return _pathway_explore_response(name, usage, turn.stage, options)
            features = extract_features(turn.archive["profile"], turn.message)
            directions = _prioritize_directions(analyze_directions(features), turn.facts)
            selection = select_questions(["confirmed_direction", "daily_learning_hours"], turn.facts, turn.history["asked_fields"], question_only_streak=0)
            turn.questions = selection["questions"]
            _record_questions(turn.history, selection["asked_fields"], question_only=False)
            turn.business.update({"features": features.to_dict(), "directions": directions, "notice": "适配分只用于方向比较，不是就业概率或人格测评。"})
            turn.archive["career"]["directions"] = directions
            return _career_explore_response(name, usage, turn.stage, directions, turn.questions)
        diagnosis = build_mentor_diagnosis(turn.facts, turn.stage, planning_confidence=turn.sufficiency["confidence"], growth_context=turn.growth_context)
        goal_plan = build_goal_plan(turn.facts, turn.stage, capacity, planning_mode=turn.sufficiency["planning_mode"], growth_context=turn.growth_context)
        location_affects_market = turn.growth_context.target_pathway in {"internship", "employment"} and bool(
            turn.growth_context.target_role or fact_value(turn.facts, "career_direction")
        )
        later = select_questions(["target_city"], turn.facts, turn.history["asked_fields"], question_only_streak=0)["questions"] if location_affects_market else []
        _record_questions(turn.history, [item["field"] for item in later], question_only=False)
        directions: list[dict[str, Any]] = []
        if fact_value(turn.facts, "career_direction"):
            directions = _prioritize_directions(analyze_directions(extract_features(turn.archive["profile"], turn.message)), turn.facts)
            turn.archive["career"]["directions"] = directions
        turn.business.update({"diagnosis": diagnosis, "goal_plan": goal_plan, "capacity": capacity, "directions": directions})
        turn.archive["academic"]["current_plan"] = goal_plan
        if fact_value(turn.facts, "direction_status") == "confirmed":
            turn.archive["career"]["confirmed_goal"] = {"primary_direction": fact_value(turn.facts, "career_direction"), "target_city": fact_value(turn.facts, "target_city", ""), "timeline": fact_value(turn.facts, "deadline_time", ""), "status": "confirmed"}
        turn.archive["onboarding_complete"] = True
        turn.archive["next_expected_update"] = ["tasks_completed", "actual_hours", "main_blocker"]
        return action_response(name, diagnosis, goal_plan, capacity, directions=directions, later_questions=later, usage=usage)

    def _persist_and_respond(self, turn: TurnContext) -> dict[str, Any]:
        turn.archive.update({"question_history": turn.history, "memory_change_summary": turn.memory_change, "profile_sufficiency": turn.sufficiency, "last_action": turn.business.get("action", turn.archive.get("last_action", ""))})
        goal_updates = dict(turn.archive.get("career", {}).get("confirmed_goal", {}))
        if not goal_updates and turn.growth_context.target_role:
            goal_updates = {
                "target_job": turn.growth_context.target_role,
                "career_goal": turn.growth_context.primary_goal,
                "goal_type": turn.growth_context.target_pathway,
                "status": "active",
            }
        persistent_write = turn.memory.persist_turn(
            user_id=turn.user_id,
            profile_updates={**turn.archive.get("profile", {}), "preferred_name": turn.archive.get("preferred_name", "")},
            profile_sources=_profile_sources(turn.facts),
            goal_updates=goal_updates,
            growth_updates={"current_stage": turn.archive.get("current_growth_stage", ""), "current_plan": turn.archive.get("academic", {}).get("current_plan", {}), "active_tasks": turn.archive.get("academic", {}).get("current_plan", {}).get("weekly_core_tasks", []), **({"current_lesson": turn.archive.get("extensions", {}).get("current_tutor", {}).get("lesson", {})} if turn.archive.get("extensions", {}).get("current_tutor") else {})},
        )
        turn.business["persistent_memory"] = {"stored": persistent_write.get("stored", False), "health": turn.memory.health()}
        proactive = self._post_process_proactive(turn)
        turn.statuses.update({"ARCHIVE": "saved_v25", "RESPONSE": "built"})
        turn.statuses.setdefault("REVIEW", "quality_checked")
        turn.statuses.setdefault("RESEARCH", "not_requested")
        turn.statuses.setdefault("IMPROVEMENT", "not_triggered")
        turn.statuses.setdefault("EVOLUTION", "not_triggered")
        turn.archive = synchronize_archive_states(turn.archive)
        save_archive(turn.archive_path, turn.archive)
        if turn.request.get("debug"):
            write_interaction_trace(self.runtime, {"state": turn.onboarding["state"], "known_facts": turn.facts, "missing_fields": turn.sufficiency["missing_blocking"], "sufficiency": turn.sufficiency, "action_selected": turn.business.get("action"), "questions_asked": [item.get("field") for item in turn.questions]})
        turn.response = normalize_response(turn.response)
        details = {"business": turn.business, "proactive": proactive}
        turn.response["details"] = details
        return result(MODULE, {"intent": turn.intent.value, "state": turn.onboarding["state"], "response": turn.response, "text": turn.response["text"], "trace": _trace(turn.statuses), "safety": turn.safety, "memory_change": turn.memory_change, "archive": turn.archive})

    @staticmethod
    def _post_process_proactive(turn: TurnContext) -> dict[str, Any]:
        history = list(turn.archive.setdefault("extensions", {}).get("proactive_feedback", []))
        last_prompt = dict(turn.archive["extensions"].get("last_proactive_prompt", {}))
        progress = {**turn.persistent_context.get("growth_state", {}), **dict(turn.request.get("progress_signals") or {})}
        previous_goal = turn.persistent_context.get("goal", {})
        target_changed = any(bool(previous_goal.get("target_city" if key == "target_city" else "target_job_raw") or previous_goal.get("target_job_normalized" if key == "target_job" else "")) and fact_value(turn.incoming, key) != (previous_goal.get("target_city") if key == "target_city" else previous_goal.get("target_job_raw") or previous_goal.get("target_job_normalized")) for key in ("target_city", "target_job") if key in turn.incoming)
        market = turn.archive.get("career", {}).get("recruitment_snapshot", {})
        signals = {"exam_days": fact_value(turn.facts, "exam_days"), "missed_tasks": turn.request.get("missed_tasks", progress.get("missed_tasks", 0)), "stress": turn.request.get("stress", 0), "completion_rate": turn.request.get("completion_rate", progress.get("completion_rate")), "actual_hours_ratio": turn.request.get("actual_hours_ratio", progress.get("actual_hours_ratio")), "job_search_days": turn.request.get("job_search_days"), "target_changed": target_changed, "market_snapshot_stale": turn.request.get("market_snapshot_stale", market.get("stale", False)), "gap_stalled_weeks": turn.request.get("gap_stalled_weeks", progress.get("gap_stalled_weeks", 0)), "weeks_without_evidence": turn.request.get("weeks_without_evidence", progress.get("weeks_without_evidence", 0))}
        engine = ProactiveEngine()
        proactive = engine.check(signals=signals, last_prompt_at=str(last_prompt.get("prompted_at", "")), feedback_history=history)
        feedback_value = str(turn.request.get("proactive_feedback", ""))
        if feedback_value:
            feedback = engine.feedback(last_prompt or proactive, feedback_value)
            history.append(feedback)
            turn.archive["extensions"]["proactive_feedback"] = history[-20:]
            turn.business["proactive_feedback"] = feedback
            if feedback_value == "rejected":
                turn.business["proactive_improvement"] = ImprovementEngine(turn.strategy_dir).observe_event(event_type="correction", pattern_key=f"proactive.false-positive.{feedback.get('reason', 'unknown')}", summary="主动建议被用户拒绝，需要降低同类触发频率", area="proactive", user_id=turn.user_id, task_id=str(turn.request.get("turn_id", "current-turn")))
        if proactive.get("should_prompt"):
            turn.archive["extensions"]["last_proactive_prompt"] = proactive
            turn.response["text"] = f"{turn.response['text']}\n\n主动建议：{proactive['message']}"
            turn.response.setdefault("mentor_sections", {})["proactive_suggestion"] = proactive["message"]
        turn.business["proactive"] = proactive
        turn.statuses["PROACTIVE"] = "prompt" if proactive["should_prompt"] else proactive["reason"]
        return proactive


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    runtime_dir = raw.get("runtime_dir") if isinstance(raw, Mapping) else None
    return CompassEngine(runtime_dir).run(raw)


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
