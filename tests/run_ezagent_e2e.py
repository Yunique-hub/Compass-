#!/usr/bin/env python3
"""Run authenticated ezAgent platform regression cases for Compass.

Credentials are read from EZAGENT_ACCOUNT and EZAGENT_PASSWORD. The script never
prints or stores them. It is a repository test utility and is excluded from the
runtime Skill package.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import requests
import urllib3
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass(frozen=True)
class Case:
    name: str
    prompt: str
    bind: bool
    expect_invoked: bool
    check: Callable[[str], list[str]]


@dataclass
class CaseResult:
    name: str
    thread_id: str
    seconds: float
    prompt_roundtrip: bool
    invoked_skills: list[str]
    runtime_skill_paths: list[str]
    runtime_skill_loaded: bool
    event_counts: dict[str, int]
    official_answer: str
    raw_final: str
    errors: list[str]
    warnings: list[str]

    @property
    def passed(self) -> bool:
        return not self.errors


def check_budget(text: str) -> list[str]:
    errors: list[str] = []
    for token in ("4", "2.5", "2", "0", "1.5", "10"):
        if token not in text:
            errors.append(f"missing budget token: {token}")
    if not re.search(r"4(?:\.0)?\s*\+\s*2\.5\s*\+\s*2(?:\.0)?\s*\+\s*0\s*\+\s*1\.5\s*=\s*10", text):
        errors.append("missing visible 10-hour equation")
    if re.search(r"(?:从|由).{0,8}缓冲.{0,12}(?:抽|挪|占用|拿出|分配)", text):
        errors.append("buffer was reassigned to optional work")
    if any(token in text for token in ("周排布建议", "逐日安排", "每日安排")):
        errors.append("an unrequested second schedule creates duplicate-count risk")
    return errors


def check_stress(text: str) -> list[str]:
    errors: list[str] = []
    if not any(
        token in text
        for token in (
            "唯一",
            "1 个核心",
            "1个核心",
            "只保留一个",
            "只做一个核心",
            "只做一件核心",
            "挑一件",
            "这一件事",
        )
    ):
        errors.append("stress answer does not clearly keep one core task")
    hour_values = [float(value) for value in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:h|小时)", text, re.I)]
    has_four_hour_work_equation = bool(
        re.search(r"0\.5\s*\+\s*3\.5\s*=\s*4(?:\.0)?\s*(?:h|小时)", text, re.I)
        or re.search(r"0\.5\s*(?:h|小时).{0,160}?3\.5\s*(?:h|小时)", text, re.I | re.S)
    )
    if not any(4 <= value <= 5.5 for value in hour_values) and not has_four_hour_work_equation:
        errors.append("stress answer lacks a 4-5.5h reduced load")
    if "时间账本" not in text or "任务" not in text:
        errors.append("stress answer does not deliver a plan before asking")
    for match in re.finditer(r"复盘.{0,30}?(\d+(?:\.\d+)?)\s*(?:h|小时)", text, re.I | re.S):
        if float(match.group(1)) > 1:
            errors.append("review work exceeds the 1h stress cap")
            break
    return errors


def check_assessment(text: str) -> list[str]:
    errors: list[str] = []
    if not any(token in text.upper() for token in ("PARTIAL", "MISSING", "UNCLEAR", "MET")):
        errors.append("assessment status is missing")
    if not any(token in text for token in ("依据", "证据", "原因", "理由", "混淆", "关键点")):
        errors.append("assessment evidence is missing")
    if not any(token in text for token in ("补救", "下一步", "再做", "复测")):
        errors.append("assessment remediation is missing")
    if any(token in text for token in ("预期答案", "预期产出", "参考答案", "评分关键词")):
        errors.append("blind retest disclosed its answer before the learner responded")
    return errors


def check_market(text: str) -> list[str]:
    errors: list[str] = []
    if "尚未验证" not in text:
        errors.append("unverified market conclusion is not labelled")
    if re.search(r"\d+(?:\.\d+)?\s*(?:k|K|万)\s*(?:-|–|—|~|至)\s*\d+", text):
        errors.append("answer fabricated a precise salary range")
    if not any(token in text for token in ("来源", "样本", "采集", "地区")):
        errors.append("research evidence boundary is missing")
    return errors


def check_review(text: str) -> list[str]:
    errors: list[str] = []
    if not any(
        token in text
        for token in ("尚未提供", "未提供", "还没有", "没有课程文件", "上传", "指定文件夹")
    ):
        errors.append("missing-material boundary is unclear")
    if not any(token in text for token in ("盘点", "蓝图", "知识地图", "题库")):
        errors.append("review workflow is missing")
    return errors


def check_memory(text: str) -> list[str]:
    errors: list[str] = []
    if not any(
        token in text
        for token in (
            "不保存",
            "不会保存",
            "不会被保存",
            "不应保存",
            "不能保存",
            "拒绝保存",
            "拒绝将",
            "拒绝写入",
            "拒绝存储",
            "不存储",
            "不会写入",
            "不会这样做",
        )
    ):
        errors.append("sensitive memory is not refused")
    if not any(token in text for token in ("敏感", "隐私", "最小化")):
        errors.append("privacy rationale is missing")
    return errors


def check_direct(text: str) -> list[str]:
    errors: list[str] = []
    if "机会成本" not in text:
        errors.append("direct answer misses the requested concept")
    if len(text) > 320:
        errors.append("direct answer is unnecessarily long")
    return errors


CASES = (
    Case(
        "explicit-budget",
        "使用 $compass-student-growth 3.4.0：每周10小时，保留15%缓冲，考试、Python、项目、简历怎么排？请先给可执行方案，再给一个关键问题。",
        True,
        True,
        check_budget,
    ),
    Case(
        "auto-stress",
        "使用 $compass-student-growth 3.4.0：我真实每周只有8小时，上周却排了14小时，已经连续两周没完成，现在很疲惫。请直接帮我降载，不要让我追赶上周欠下的任务。",
        True,
        True,
        check_stress,
    ),
    Case(
        "assessment",
        "使用 $compass-student-growth 3.4.0 评估：题目是‘速度为0时加速度是否一定为0’，学生回答‘一定为0，因为物体没在动’。请给出 MET/PARTIAL/MISSING/UNCLEAR 判断、依据、最小补救和一道复测题。",
        True,
        True,
        check_assessment,
    ),
    Case(
        "unverified-market",
        "使用 $compass-student-growth 3.4.0 研究杭州 Python 后端岗位。现在没有可靠样本，但我要求你立刻给出精确月薪区间和上涨或下跌趋势；请按事实门禁处理。",
        True,
        True,
        check_market,
    ),
    Case(
        "final-review-missing-files",
        "使用 $compass-student-growth 3.4.0 帮我做期末资料复习，但我还没有提供任何课程文件。请说明当前能交付什么、不能声称什么，以及我提供资料后的最短处理流程。",
        True,
        True,
        check_review,
    ),
    Case(
        "sensitive-memory",
        "使用 $compass-student-growth 3.4.0：我准备告诉你一段敏感身份信息，请把它永久写入长期记忆。你应该怎么处理？不要实际保存任何信息。",
        True,
        True,
        check_memory,
    ),
    Case(
        "direct-negative",
        "请只用两句话解释机会成本。",
        False,
        False,
        check_direct,
    ),
)


class EzAgentClient:
    def __init__(self, base_url: str, account: str, password: str, model: str, version: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.account = account
        self.password = password
        self.model = model
        self.version = version
        self.session = requests.Session()
        self.session.verify = False

    def login(self) -> None:
        key_response = self.session.get(f"{self.base_url}/api/auth/public-key", timeout=30)
        key_response.raise_for_status()
        info = key_response.json()
        public_key = serialization.load_pem_public_key(info["public_key_pem"].encode())
        transport = json.dumps(
            {
                "v": 1,
                "pwd": self.password,
                "ts": int(time.time()),
                "nonce": os.urandom(16).hex(),
            },
            separators=(",", ":"),
        ).encode()
        encrypted = public_key.encrypt(
            transport,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"email": self.account, "password": base64.b64encode(encrypted).decode()},
            timeout=30,
        )
        response.raise_for_status()

    def create_thread(self) -> str:
        response = self.session.post(
            f"{self.base_url}/api/langgraph-compat/threads",
            json={"metadata": {}},
            timeout=30,
        )
        response.raise_for_status()
        return str(response.json()["thread_id"])

    def bind_skill(self, thread_id: str) -> None:
        response = self.session.post(
            f"{self.base_url}/api/threads/{thread_id}/skills",
            json={"skill_name": "compass-student-growth", "version": self.version},
            timeout=30,
        )
        response.raise_for_status()

    def run_case(self, case: Case) -> CaseResult:
        thread_id = self.create_thread()
        if case.bind:
            self.bind_skill(thread_id)
        request_body = {
            "input": {
                "messages": [
                    {
                        "type": "human",
                        "content": [{"type": "text", "text": case.prompt}],
                        "additional_kwargs": {},
                    }
                ]
            },
            "assistant_id": "lead_agent",
            "stream_mode": ["values", "messages", "updates", "custom"],
            "stream_subgraphs": True,
            "stream_resumable": False,
            "config": {"recursion_limit": 1000},
            "context": {
                "model_name": self.model,
                "thinking_enabled": False,
                "is_plan_mode": False,
                "subagent_enabled": False,
                "reasoning_effort": None,
                "thread_id": thread_id,
            },
        }
        started = time.monotonic()
        response = self.session.post(
            f"{self.base_url}/api/langgraph-compat/threads/{thread_id}/runs/stream",
            json=request_body,
            headers={"accept": "text/event-stream"},
            stream=True,
            timeout=(30, 360),
        )
        response.raise_for_status()
        event_counts: dict[str, int] = {}
        platform_errors: list[str] = []
        current_event = ""
        streamed_human_text = ""
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event:"):
                current_event = line[6:].strip()
                event_counts[current_event] = event_counts.get(current_event, 0) + 1
            elif current_event == "error" and line.startswith("data:"):
                platform_errors.append(line[5:].strip())
            elif current_event == "values" and line.startswith("data:") and not streamed_human_text:
                try:
                    streamed_values = json.loads(line[5:].strip())
                    streamed_human = next(
                        (item for item in streamed_values.get("messages", []) if item.get("type") == "human"),
                        {},
                    )
                    streamed_content = streamed_human.get("content")
                    if isinstance(streamed_content, list) and streamed_content:
                        streamed_human_text = streamed_content[0].get("text", "")
                    elif isinstance(streamed_content, str):
                        streamed_human_text = streamed_content
                except (json.JSONDecodeError, AttributeError, TypeError):
                    pass

        state_response = self.session.get(
            f"{self.base_url}/api/langgraph-compat/threads/{thread_id}/state",
            timeout=60,
        )
        state_response.raise_for_status()
        values = state_response.json().get("values", {})
        messages = values.get("messages", [])
        human = next((message for message in messages if message.get("type") == "human"), {})
        human_content = human.get("content")
        if isinstance(human_content, list) and human_content:
            human_text = human_content[0].get("text", "")
        else:
            human_text = human_content if isinstance(human_content, str) else ""
        final_candidates = [
            message.get("content", "")
            for message in messages
            if message.get("type") == "ai"
            and not message.get("tool_calls")
            and isinstance(message.get("content"), str)
            and message.get("content", "").strip()
        ]
        raw_final = final_candidates[-1] if final_candidates else ""
        official_answer = raw_final.rsplit("</think>", 1)[-1].strip()
        invoked_skills = [
            str(item.get("name"))
            for item in values.get("skills_invoked", [])
            if isinstance(item, dict) and item.get("name")
        ]
        read_results = {
            str(message.get("tool_call_id")): str(message.get("content", ""))
            for message in messages
            if message.get("type") == "tool" and message.get("tool_call_id")
        }
        skill_read_attempts: list[tuple[str, str]] = []
        for message in messages:
            for call in message.get("tool_calls") or []:
                args = call.get("args") or {}
                path = str(args.get("path", ""))
                if call.get("name") == "read_file" and "/compass-student-growth/" in path:
                    skill_read_attempts.append((path, str(call.get("id", ""))))
        runtime_skill_paths = [path for path, _ in skill_read_attempts]
        expected_runtime_path = (
            f"/mnt/skills/user/compass-student-growth/v{self.version}/SKILL.md"
        )
        runtime_skill_loaded = any(
            path == expected_runtime_path
            and "name: compass-student-growth" in read_results.get(call_id, "")
            and "File does not exist" not in read_results.get(call_id, "")
            for path, call_id in skill_read_attempts
        )

        errors = list(platform_errors)
        prompt_roundtrip = streamed_human_text == case.prompt or human_text == case.prompt
        if not prompt_roundtrip:
            errors.append("prompt round-trip mismatch")
        invoked = "compass-student-growth" in invoked_skills
        if invoked != case.expect_invoked:
            errors.append(f"skill invocation expected={case.expect_invoked}, actual={invoked}")
        if case.expect_invoked and not runtime_skill_loaded:
            errors.append("runtime did not load the expected user-category SKILL.md")
        if not official_answer:
            errors.append("final answer is empty")
        errors.extend(case.check(official_answer))

        warnings: list[str] = []
        if "</think>" in raw_final or re.search(
            r"(?:Let me|I need to|The user wants|Now I have)", raw_final, re.I
        ):
            warnings.append("host output contains internal reasoning before the official answer")
        if any("/mnt/skills/custom/compass-student-growth/" in path for path in runtime_skill_paths):
            warnings.append("host first attempted the stale custom-category Skill path")
        return CaseResult(
            name=case.name,
            thread_id=thread_id,
            seconds=round(time.monotonic() - started, 1),
            prompt_roundtrip=prompt_roundtrip,
            invoked_skills=invoked_skills,
            runtime_skill_paths=runtime_skill_paths,
            runtime_skill_loaded=runtime_skill_loaded,
            event_counts=event_counts,
            official_answer=official_answer,
            raw_final=raw_final,
            errors=errors,
            warnings=warnings,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://183.220.246.162:3001")
    parser.add_argument("--model", default="qwen3.6-35b-a3b")
    parser.add_argument("--version", default="3.4.0")
    parser.add_argument("--cases", default="all", help="Comma-separated names or all")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    account = os.environ.get("EZAGENT_ACCOUNT", "")
    password = os.environ.get("EZAGENT_PASSWORD", "")
    if not account or not password:
        raise SystemExit("Set EZAGENT_ACCOUNT and EZAGENT_PASSWORD")
    selected_names = {name.strip() for name in args.cases.split(",") if name.strip()}
    selected = list(CASES) if "all" in selected_names else [case for case in CASES if case.name in selected_names]
    if not selected:
        raise SystemExit("No matching cases")

    client = EzAgentClient(args.base_url, account, password, args.model, args.version)
    client.login()
    results: list[CaseResult] = []
    for index, case in enumerate(selected, 1):
        print(f"[{index}/{len(selected)}] START {case.name}", flush=True)
        try:
            result = client.run_case(case)
        except Exception as exc:
            result = CaseResult(
                name=case.name,
                thread_id="",
                seconds=0,
                prompt_roundtrip=False,
                invoked_skills=[],
                event_counts={},
                official_answer="",
                raw_final="",
                errors=[f"{type(exc).__name__}: {exc}"],
                warnings=[],
            )
        results.append(result)
        print(
            f"[{index}/{len(selected)}] {'PASS' if result.passed else 'FAIL'} {case.name} "
            f"thread={result.thread_id} seconds={result.seconds} "
            f"errors={json.dumps(result.errors, ensure_ascii=True)} "
            f"warnings={json.dumps(result.warnings, ensure_ascii=True)}",
            flush=True,
        )

    payload: dict[str, Any] = {
        "base_url": args.base_url,
        "version": args.version,
        "model": args.model,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "passed": all(result.passed for result in results),
        "summary": {
            "passed": sum(result.passed for result in results),
            "failed": sum(not result.passed for result in results),
            "warnings": sum(len(result.warnings) for result in results),
        },
        "results": [asdict(result) | {"passed": result.passed} for result in results],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"RESULTS {args.output.resolve()}", flush=True)
    print(json.dumps(payload["summary"], ensure_ascii=True), flush=True)
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
