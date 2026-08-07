"""Deterministic intent routing for the public Compass entry point."""

from __future__ import annotations

from enum import Enum
from typing import Any, Sequence


class Intent(str, Enum):
    ONBOARDING = "ONBOARDING"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    CAREER_EXPLORE = "CAREER_EXPLORE"
    CAREER_CONFIRM = "CAREER_CONFIRM"
    DESTINATION_CONFIRM = "DESTINATION_CONFIRM"
    RECRUITMENT_ANALYSIS = "RECRUITMENT_ANALYSIS"
    JD_ANALYSIS = "JD_ANALYSIS"
    CAREER_GAP = "CAREER_GAP"
    LEARNING_PLAN = "LEARNING_PLAN"
    WEEKLY_PLAN = "WEEKLY_PLAN"
    COURSE_LEARNING = "COURSE_LEARNING"
    EXAM_REVIEW = "EXAM_REVIEW"
    QUESTION_PRACTICE = "QUESTION_PRACTICE"
    MISTAKE_REVIEW = "MISTAKE_REVIEW"
    RESOURCE_SEARCH = "RESOURCE_SEARCH"
    PROGRESS_REVIEW = "PROGRESS_REVIEW"
    MEMORY_QUERY = "MEMORY_QUERY"
    MEMORY_UPDATE = "MEMORY_UPDATE"
    MEMORY_FORGET = "MEMORY_FORGET"
    STRATEGY_FEEDBACK = "STRATEGY_FEEDBACK"
    TARGET_CITY_UPDATE = "TARGET_CITY_UPDATE"
    TARGET_JOB_UPDATE = "TARGET_JOB_UPDATE"
    GAP_ANALYSIS = "GAP_ANALYSIS"
    PLAN_ADJUSTMENT = "PLAN_ADJUSTMENT"
    START_LEARNING = "START_LEARNING"
    CONTINUE_LEARNING = "CONTINUE_LEARNING"
    SUBMIT_EXERCISE = "SUBMIT_EXERCISE"
    SUBMIT_EVIDENCE = "SUBMIT_EVIDENCE"
    GENERAL_SUPPORT = "GENERAL_SUPPORT"


def _contains(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def route_intent(message: str, attachments: Sequence[Any] | None = None) -> Intent:
    text = str(message or "").strip().lower()
    attachment_names = " ".join(
        str(item.get("name", "") if isinstance(item, dict) else item).lower()
        for item in (attachments or [])
    )
    combined = f"{text} {attachment_names}"

    if _contains(text, "忘记", "删除我的记忆", "关闭长期记忆"):
        return Intent.MEMORY_FORGET
    if _contains(text, "你记住了什么", "继续上次", "恢复进度", "上次进度"):
        return Intent.MEMORY_QUERY
    if _contains(text, "记住", "目标城市改成", "学习习惯改成"):
        return Intent.MEMORY_UPDATE
    if _contains(text, "太多", "做不完", "不喜欢长视频", "计划不现实", "周末没完成"):
        return Intent.STRATEGY_FEEDBACK
    if _contains(text, "提交练习", "这是我的答案", "练习完成", "实验完成", "完成域创建"):
        return Intent.SUBMIT_EXERCISE
    if _contains(text, "提交证据", "这是我的作品", "这是项目链接"):
        return Intent.SUBMIT_EVIDENCE
    if _contains(text, "继续学习", "继续这节", "接着学"):
        return Intent.CONTINUE_LEARNING
    if _contains(text, "开始学习", "开始学", "现在学", "带我学"):
        return Intent.START_LEARNING
    if _contains(text, "错题", "答错", "做错"):
        return Intent.MISTAKE_REVIEW
    if _contains(text, "出题", "练习题", "刷题"):
        return Intent.QUESTION_PRACTICE
    if _contains(combined, "考试", "期末", "复习", "真题", ".ppt", ".pptx"):
        return Intent.EXAM_REVIEW
    if _contains(text, "课程学习", "这门课", "预习", "课程怎么学"):
        return Intent.COURSE_LEARNING
    if _contains(text, "这个jd", "这个 jd", "岗位描述", "职位描述"):
        return Intent.JD_ANALYSIS
    if _contains(text, "我决定", "确定做", "主方向", "选择java", "选择 java"):
        return Intent.CAREER_CONFIRM
    if _contains(text, "想去", "目标城市", "去杭州", "去上海", "春招", "秋招"):
        return Intent.DESTINATION_CONFIRM
    if _contains(text, "招聘要求", "岗位要求", "现在杭州", "市场需要"):
        return Intent.RECRUITMENT_ANALYSIS
    if _contains(text, "能力差距", "还缺什么", "短板"):
        return Intent.GAP_ANALYSIS
    if _contains(text, "本周计划", "每周计划", "weekly"):
        return Intent.WEEKLY_PLAN
    if _contains(text, "学习计划", "成长计划", "大学学习"):
        return Intent.LEARNING_PLAN
    if _contains(text, "找资料", "学习资源", "查一下", "搜索"):
        return Intent.RESOURCE_SEARCH
    if _contains(text, "复盘", "完成率", "进度怎么样"):
        return Intent.PROGRESS_REVIEW
    if _contains(text, "不知道毕业", "适合什么工作", "职业方向", "挺迷茫", "迷茫"):
        return Intent.CAREER_EXPLORE
    return Intent.GENERAL_SUPPORT
