from scripts.competency.evidence_engine import EvidenceEngine
from scripts.competency.gap_engine import GapEngine
from scripts.learning.adaptive_planner import AdaptivePlanner
from scripts.learning.assessment_engine import AssessmentEngine
from scripts.learning.tutor_engine import TutorEngine


def test_market_gap_plan_tutor_assessment_evidence_competency_replan() -> None:
    stats = [{"skill": "Active Directory", "frequency": 0.8, "importance": 0.9, "job_ids": ["j1", "j2"]}]
    gaps = GapEngine().calculate(stats, {})
    market = {"market_data_status": "insufficient", "synthetic": True, "snapshot_id": "synthetic-s1"}
    goal = {"target_city": "杭州", "target_job_normalized": "IT支持", "job_search_time": "明年实习"}
    planner = AdaptivePlanner()
    plan = planner.build(goal=goal, market=market, gaps=gaps, weekly_hours=8)
    assert not plan["formal_plan_generated"] and plan["mode"] == "preliminary" and len(plan["weekly_core_tasks"]) == 1
    task = plan["weekly_core_tasks"][0]
    assert task["market_evidence"] and task["gap_reference"] and "尚未经过" in plan["notice"]
    tutor = TutorEngine().start(task, job_context="杭州 IT支持")
    criteria = tutor["exercise"]["acceptance_criteria"]
    assessment = AssessmentEngine().evaluate(skill="Active Directory", submission={"criteria_met": criteria}, criteria=criteria)
    evidence_engine = EvidenceEngine()
    evidence = evidence_engine.create(skill="Active Directory", evidence_type="assessment", source="test", description="AD Lab", assessment=assessment)
    competency = evidence_engine.update_competency({}, evidence)
    new_gaps = GapEngine().calculate(stats, {"Active Directory": competency})
    replanned = planner.replan(previous=plan, goal=goal, market=market, gaps=new_gaps, weekly_hours=8, reason="verified_competency_changed")
    assert assessment["passed"] and evidence["verification_status"] == "verified"
    assert competency["verified_level"] > 0 and new_gaps[0]["gap_level"] < gaps[0]["gap_level"]
    assert replanned["supersedes"] == plan["plan_id"]


def test_claimed_skill_without_evidence_does_not_reduce_gap() -> None:
    gap = GapEngine().calculate([{"skill": "Python", "frequency": 1.0}], {"Python": {"claimed_level": 0.9, "verified_level": 0.9, "evidence": []}})[0]
    assert gap["verified_level"] == 0.0 and gap["gap_level"] > 0
