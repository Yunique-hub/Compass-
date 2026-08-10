"""Validate Compass structure, schemas, imports, behavior and package boundaries."""
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

try:
    from .io_utils import result, write_json
except ImportError:
    from io_utils import result, write_json

MODULE = "validate_package"
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODES = {"skill", "dev", "full"}

RUNTIME_FILES = {
    "SKILL.md", "manifest.yaml", "pyproject.toml", "LICENSE", "THIRD_PARTY_NOTICES.md",
    "scripts/compass_engine.py", "scripts/archive_v2.py", "scripts/core/turn_context.py",
    "scripts/core/intent_router.py", "scripts/core/response_builder.py", "scripts/core/growth_context.py",
    "scripts/academic/major_engine.py", "scripts/academic/pathway_engine.py", "reference/academic_profiles.json",
    "scripts/memory/memory_engine.py", "scripts/memory/backends/sqlite_backend.py",
    "reference/open_source/upstream-lock.json", "reference/schemas/user_profile.schema.json",
}
DEV_FILES = {"README.md", "DEVELOPMENT_REPORT.md", "ENVIRONMENT_BASELINE.md", "scripts/pack_skill.py", "scripts/validate_package.py"}
IMPORTS = (
    "scripts.compass_engine", "scripts.core.intent_router", "scripts.core.response_builder",
    "scripts.memory.memory_engine", "scripts.recruitment.recruitment_engine",
    "scripts.learning.tutor_engine", "scripts.learning.assessment_engine", "scripts.review.review_engine",
)
FORBIDDEN_PARTS = {".git", "__pycache__", ".pytest_cache", ".test-deps", ".venv", "venv", "node_modules", "runtime", "dist"}
FORBIDDEN_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3", ".tmp"}


def parse_manifest(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^(name|version|scope):\s*(.+)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"\'')
    return values


def _required(mode: str) -> set[str]:
    return RUNTIME_FILES | (DEV_FILES if mode in {"dev", "full"} else set())


def _validate_structure(root: Path, mode: str, errors: list[dict[str, Any]]) -> None:
    for relative in sorted(_required(mode)):
        if not (root / relative).is_file():
            errors.append({"code": "MISSING_FILE", "message": relative})
    if mode in {"dev", "full"}:
        for directory in ("tests/unit", "tests/integration"):
            if not list((root / directory).glob("test_*.py")):
                errors.append({"code": "TESTS_MISSING", "message": directory})


def _validate_metadata(root: Path, errors: list[dict[str, Any]]) -> dict[str, str]:
    manifest = parse_manifest((root / "manifest.yaml").read_text(encoding="utf-8"))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest.get("name", "")):
        errors.append({"code": "INVALID_NAME", "message": manifest.get("name", "")})
    if not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")):
        errors.append({"code": "INVALID_VERSION", "message": manifest.get("version", "")})
    if manifest.get("scope") != "private":
        errors.append({"code": "INVALID_SCOPE", "message": manifest.get("scope", "")})
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if not version_match or version_match.group(1) != manifest.get("version"):
        errors.append({"code": "VERSION_MISMATCH", "message": "manifest.yaml 与 pyproject.toml 版本不一致"})
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    if not re.match(r"^---\nname: compass-student-growth\ndescription: [^\n]+\n---\n", skill):
        errors.append({"code": "SKILL_FRONTMATTER_INVALID", "message": "frontmatter 必须仅含有效 name 和 description"})
    return manifest


def _validate_json_and_schemas(root: Path, errors: list[dict[str, Any]]) -> int:
    paths = [*sorted((root / "config").glob("*.json")), *sorted((root / "reference").rglob("*.json"))]
    documents: dict[Path, Any] = {}
    for path in paths:
        try:
            documents[path] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append({"code": "INVALID_JSON", "message": f"{path.relative_to(root)}: {exc}"})
    try:
        from jsonschema.validators import validator_for

        for path, document in documents.items():
            if "schemas" in path.parts:
                try:
                    validator_for(document).check_schema(document)
                except Exception as exc:  # jsonschema exposes validator-specific subclasses
                    errors.append({"code": "INVALID_SCHEMA", "message": f"{path.relative_to(root)}: {exc}"})
    except ImportError:
        errors.append({"code": "IMPORT_FAILED", "message": "jsonschema dependency unavailable"})
    return len(paths)


def _validate_imports(errors: list[dict[str, Any]]) -> None:
    importlib.invalidate_caches()
    for module in IMPORTS:
        try:
            importlib.import_module(module)
        except Exception as exc:
            errors.append({"code": "IMPORT_FAILED", "message": f"{module}: {exc}"})


def _validate_behavior(errors: list[dict[str, Any]]) -> None:
    try:
        from scripts.compass_engine import CompassEngine

        with tempfile.TemporaryDirectory(prefix="compass-validator-") as directory:
            engine = CompassEngine(Path(directory))
            actionable = engine.run({"user_id": "validator-action", "message": "我是大二计算机专业，学过 Python，明年找后端实习，现在怎么准备？"})["data"]
            response = actionable["response"]
            required = {"current_judgment", "current_goal", "do_now", "why", "next_step", "questions"}
            if not required.issubset(response) or not response["do_now"] or not response["current_goal"]:
                errors.append({"code": "ACTION_CONTRACT_FAILED", "message": "首轮行动或统一响应契约不满足"})
            if actionable["trace"] and [item["step"] for item in actionable["trace"]] != ["SAFETY", "RESTORE", "UNDERSTAND", "DECIDE", "EXECUTE", "LEARN", "PERSIST", "RESPOND"]:
                errors.append({"code": "PIPELINE_CONTRACT_FAILED", "message": "运行 trace 与统一 pipeline 不一致"})
            simple = engine.run({"user_id": "validator-simple", "message": "Python 列表和元组有什么区别？"})["data"]
            if simple["intent"] != "KNOWLEDGE_QA" or "未来 12 个月" in simple["text"]:
                errors.append({"code": "SIMPLE_RESPONSE_FAILED", "message": "简单问题被过度结构化"})
            domain_cases = (
                ("finance", "金融大二，想进投行。", "finance_accounting", ("估值", "金融建模"), ("FastAPI", "临床轮转")),
                ("law", "法学大三，准备法考并找律所实习。", "law", ("案例分析", "法律检索"), ("FastAPI", "GitHub")),
                ("unknown", "葡萄与葡萄酒工程大二，现在该怎么规划？", "agriculture_environment", ("自然科学", "需要验证"), ("不支持", "LeetCode")),
            )
            for case, message, family, required_terms, forbidden_terms in domain_cases:
                output = engine.run({"user_id": f"validator-{case}", "message": message})["data"]
                business = output["response"]["details"]["business"]
                context = business.get("growth_context", {})
                corpus = output["text"] + json.dumps(context, ensure_ascii=False)
                if context.get("academic_profile", {}).get("discipline_family") != family or not all(term in corpus for term in required_terms):
                    errors.append({"code": "DOMAIN_CONTEXT_FAILED", "message": case})
                if any(term in corpus for term in forbidden_terms):
                    errors.append({"code": "DOMAIN_LEAKAGE", "message": case})
    except Exception as exc:
        errors.append({"code": "BEHAVIOR_CHECK_CRASHED", "message": str(exc)})


def _validate_upstream(root: Path, mode: str, errors: list[dict[str, Any]]) -> None:
    lock = json.loads((root / "reference/open_source/upstream-lock.json").read_text(encoding="utf-8"))
    for name, expected in lock.get("projects", {}).items():
        license_dir = root / "licenses" / name
        if not license_dir.is_dir() or not any(path.is_file() for path in license_dir.rglob("*")):
            errors.append({"code": "LICENSE_OR_AUTHORIZATION_MISSING", "message": name})
        if mode != "full":
            continue
        marker_path = root / "vendor" / name / ".upstream-source.json"
        if not marker_path.is_file():
            errors.append({"code": "UPSTREAM_MARKER_MISSING", "message": name})
            continue
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if any(marker.get(key) != expected.get(key) for key in ("repository", "branch", "commit")):
            errors.append({"code": "UPSTREAM_MARKER_MISMATCH", "message": name})
        if (root / "vendor" / name / ".git").exists():
            errors.append({"code": "NESTED_GIT_FORBIDDEN", "message": name})


def validate_directory(root: Path = ROOT, *, mode: str = "skill") -> dict[str, Any]:
    if mode not in MODES:
        return result(MODULE, {"valid": False, "mode": mode}, ok=False, errors=[{"code": "INVALID_MODE", "message": mode}])
    errors: list[dict[str, Any]] = []
    _validate_structure(root, mode, errors)
    if errors:
        return result(MODULE, {"valid": False, "mode": mode}, ok=False, errors=errors)
    manifest = _validate_metadata(root, errors)
    json_count = _validate_json_and_schemas(root, errors)
    _validate_imports(errors)
    _validate_behavior(errors)
    _validate_upstream(root, mode, errors)
    return result(MODULE, {"valid": not errors, "root": str(root), "mode": mode, "version": manifest.get("version", ""), "json_files": json_count, "behavior_checks": 6}, ok=not errors, errors=errors)


def validate_zip(path: Path, *, mode: str = "skill") -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    if mode not in MODES:
        return result(MODULE, {"valid": False, "mode": mode}, ok=False, errors=[{"code": "INVALID_MODE", "message": mode}])
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            for name in sorted(_required(mode)):
                if name not in names:
                    errors.append({"code": "ZIP_REQUIRED_MISSING", "message": name})
            forbidden = [name for name in names if any(part in FORBIDDEN_PARTS for part in Path(name).parts) or Path(name).suffix in FORBIDDEN_SUFFIXES]
            if forbidden:
                errors.append({"code": "ZIP_FORBIDDEN_CONTENT", "message": forbidden[:10]})
            has_vendor = any(name.startswith("vendor/") for name in names)
            if mode == "full" and not has_vendor:
                errors.append({"code": "FULL_VENDOR_MISSING", "message": "vendor/"})
            if mode != "full" and has_vendor:
                errors.append({"code": "VENDOR_FORBIDDEN", "message": f"{mode} 包不得包含 vendor 源码"})
            if mode == "skill" and any(name.startswith("tests/") or name in DEV_FILES for name in names):
                errors.append({"code": "SKILL_DEV_CONTENT_FORBIDDEN", "message": "skill 包含测试或开发文档"})
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append({"code": "ZIP_INVALID", "message": str(exc)})
    return result(MODULE, {"valid": not errors, "zip": str(path), "mode": mode}, ok=not errors, errors=errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=sorted(MODES), default="skill")
    parser.add_argument("--zip", type=Path)
    args = parser.parse_args()
    payload = validate_zip(args.zip, mode=args.mode) if args.zip else validate_directory(mode=args.mode)
    write_json(payload)
    raise SystemExit(0 if payload["ok"] else 2)
