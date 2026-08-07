"""仅使用标准库校验 Skill 目录或 zip。"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

try:
    from .io_utils import result, write_json
except ImportError:
    from io_utils import result, write_json

MODULE = "validate_package"
ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "SKILL.md", "manifest.yaml", "README.md", "pyproject.toml", ".gitignore",
    "config/memory_policy.json", "config/plan_rules.json", "DEVELOPMENT_REPORT.md",
    "ENVIRONMENT_BASELINE.md", "THIRD_PARTY_NOTICES.md", ".env.example", "docker-compose.yml",
    "scripts/compass_engine.py", "scripts/archive_v2.py", "scripts/bootstrap_dev.py", "scripts/demo_v2.py",
    "scripts/core/intent_router.py", "scripts/core/state_machine.py", "scripts/core/context_builder.py",
    "scripts/career/profile_engine.py", "scripts/career/direction_engine.py",
    "scripts/academic/capacity_engine.py", "scripts/review/review_engine.py",
    "scripts/memory/memory_engine.py", "scripts/improvement/improvement_engine.py",
    "scripts/evolution/evolution_engine.py", "scripts/research/research_engine.py",
    "scripts/proactive/proactive_engine.py", "reference/open_source/upstream-lock.json",
    "scripts/models.py", "scripts/io_utils.py", "scripts/profile_parser.py", "scripts/career_direction_analyzer.py",
    "scripts/direction_confirmation.py", "scripts/recruitment_data_processor.py", "scripts/jd_analyzer.py",
    "scripts/competency_gap.py", "scripts/plan_generator.py", "scripts/plan_validator.py", "scripts/resource_matcher.py",
    "scripts/archive_import.py", "scripts/archive_export.py", "scripts/memory_classifier.py", "scripts/memory_policy.py",
    "scripts/memory_store.py", "scripts/memory_retriever.py", "scripts/conflict_resolver.py", "scripts/safety_router.py",
    "scripts/demo_pipeline.py", "scripts/validate_package.py", "scripts/pack_skill.py",
    "tests/e2e/manual_cases.md",
]
REQUIRED_SKILL_TERMS = [
    "身份和角色定位", "适用场景", "何时不该使用", "核心原则", "对话状态机", "冷启动建档",
    "就业方向分析", "用户确认门", "招聘数据分析", "JD 分析", "岗位胜任力差距", "三级学习规划",
    "资源推荐", "长期记忆", "状态关怀与安全路由",
    "数据来源、引用和时效", "异常处理和降级", "标准输出格式", "输出质检清单", "示例 4",
    "Review Brain", "Memory Brain", "Improvement Brain", "Evolution Brain", "Research Brain", "Proactive Brain",
    "统一执行顺序", "Growth Archive v2", "统一周时间预算",
]


def parse_manifest(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^(name|version|scope):\s*(.+)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip()
    description_match = re.search(r"^description:\s*>-\s*\n(?P<body>(?:\s{2,}.*\n?)+)", text, re.MULTILINE)
    values["description"] = " ".join(line.strip() for line in description_match.group("body").splitlines()) if description_match else ""
    return values


def validate_directory(root: Path = ROOT) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append({"code": "MISSING_FILE", "message": relative})
    if errors:
        return result(MODULE, {"valid": False}, ok=False, errors=errors)
    manifest_text = (root / "manifest.yaml").read_text(encoding="utf-8")
    manifest = parse_manifest(manifest_text)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest.get("name", "")):
        errors.append({"code": "INVALID_NAME", "message": "manifest name 必须为 kebab-case"})
    if not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")):
        errors.append({"code": "INVALID_VERSION", "message": "manifest version 必须为语义化版本"})
    if manifest.get("scope") != "private":
        errors.append({"code": "INVALID_SCOPE", "message": "scope 必须为 private"})
    if manifest.get("version") != "2.0.0":
        errors.append({"code": "VERSION_NOT_V2", "message": manifest.get("version", "")})
    for term in ("就业方向分析", "公开招聘数据", "JD", "学习规划", "成长复盘", "长期记忆"):
        if term not in manifest.get("description", ""):
            errors.append({"code": "DESCRIPTION_TERM_MISSING", "message": term})
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    if not re.match(r"^---\nname: compass-student-growth\ndescription: .+?\n---\n", skill, re.DOTALL):
        errors.append({"code": "SKILL_FRONTMATTER_INVALID", "message": "SKILL.md frontmatter 必须仅含 name 和 description"})
    for term in REQUIRED_SKILL_TERMS:
        if term not in skill:
            errors.append({"code": "SKILL_SECTION_MISSING", "message": term})
    if not 5000 <= len(skill) <= 20000:
        errors.append({"code": "SKILL_LENGTH_INVALID", "message": f"SKILL.md 字符数应在 5000-20000，实际 {len(skill)}"})
    json_files = list((root / "config").glob("*.json")) + list((root / "reference").rglob("*.json"))
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append({"code": "INVALID_JSON", "message": f"{path.relative_to(root)}: {exc}"})
    snapshots = list((root / "reference" / "recruitment_snapshots" / "cities").rglob("*.json"))
    for path in snapshots:
        raw = json.loads(path.read_text(encoding="utf-8"))
        for field in ("snapshot_version", "collected_at", "date_range", "synthetic", "jobs"):
            if field not in raw:
                errors.append({"code": "SNAPSHOT_FIELD_MISSING", "message": f"{path.name}: {field}"})
        if raw.get("synthetic"):
            if raw.get("usage_notice") != "仅用于功能测试，不代表当前市场":
                errors.append({"code": "SYNTHETIC_NOTICE_INVALID", "message": path.name})
            if any(job.get("source") != "synthetic-test-fixture" for job in raw.get("jobs", [])):
                errors.append({"code": "SYNTHETIC_SOURCE_INVALID", "message": path.name})
        if any(not job.get("source") for job in raw.get("jobs", [])):
            errors.append({"code": "SOURCE_MISSING", "message": path.name})
    resources = json.loads((root / "reference" / "resources" / "cs_resources.json").read_text(encoding="utf-8"))["resources"]
    for item in resources:
        if not item.get("verified"):
            warnings.append({"code": "RESOURCE_REQUIRES_REVIEW", "message": item["resource_id"]})
    if not list((root / "tests" / "unit").glob("test_*.py")):
        errors.append({"code": "UNIT_TESTS_MISSING", "message": "tests/unit"})
    if not list((root / "tests" / "integration").glob("test_*.py")):
        errors.append({"code": "INTEGRATION_TESTS_MISSING", "message": "tests/integration"})
    lock = json.loads((root / "reference" / "open_source" / "upstream-lock.json").read_text(encoding="utf-8"))
    if len(lock.get("projects", {})) != 6:
        errors.append({"code": "UPSTREAM_COUNT_INVALID", "message": "必须锁定 6 个上游项目"})
    for name, expected in lock.get("projects", {}).items():
        marker_path = root / "vendor" / name / ".upstream-source.json"
        if not marker_path.is_file():
            errors.append({"code": "UPSTREAM_MARKER_MISSING", "message": name})
            continue
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if any(marker.get(key) != expected.get(key) for key in ("repository", "branch", "commit")):
            errors.append({"code": "UPSTREAM_MARKER_MISMATCH", "message": name})
        if (root / "vendor" / name / ".git").exists():
            errors.append({"code": "NESTED_GIT_FORBIDDEN", "message": name})
    for name in lock.get("projects", {}):
        license_dir = root / "licenses" / name
        if not license_dir.is_dir() or not any(path.is_file() for path in license_dir.rglob("*")):
            errors.append({"code": "LICENSE_OR_AUTHORIZATION_MISSING", "message": name})
    return result(MODULE, {"valid": not errors, "root": str(root), "checked_files": len(REQUIRED_FILES), "json_files": len(json_files), "snapshot_files": len(snapshots)}, ok=not errors, warnings=warnings, errors=errors)


def validate_zip(path: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            for name in ("SKILL.md", "manifest.yaml"):
                if name not in names:
                    errors.append({"code": "ZIP_ROOT_INVALID", "message": f"zip 根目录缺少 {name}"})
            for name in ("THIRD_PARTY_NOTICES.md", "licenses/agent-browser/LICENSE"):
                if name not in names:
                    errors.append({"code": "ZIP_NOTICE_MISSING", "message": name})
            forbidden = [name for name in names if any(part in name for part in (".git/", "__pycache__", ".pytest_cache", ".test-deps/", ".venv/")) or name.endswith((".db", ".sqlite", ".pyc"))]
            if forbidden:
                errors.append({"code": "ZIP_FORBIDDEN_CONTENT", "message": forbidden[:10]})
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append({"code": "ZIP_INVALID", "message": str(exc)})
    return result(MODULE, {"valid": not errors, "zip": str(path)}, ok=not errors, errors=errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path)
    args = parser.parse_args()
    payload = validate_zip(args.zip) if args.zip else validate_directory()
    write_json(payload)
    raise SystemExit(0 if payload["ok"] else 2)
