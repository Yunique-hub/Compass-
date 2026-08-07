"""Convert course materials to clean, traceable text without inventing content."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SOURCE_PRIORITY = {
    "past_exam": 100,
    "teacher_emphasis": 95,
    "teacher_ppt": 90,
    "homework": 80,
    "course_notes": 70,
    "textbook": 60,
    "crash_course": 50,
    "ai_generated": 10,
}


def classify_source(path: str | Path, explicit: str = "") -> str:
    if explicit in SOURCE_PRIORITY:
        return explicit
    name = Path(path).name.lower()
    rules = (
        ("past_exam", ("真题", "历年", "past_exam", "exam")),
        ("teacher_emphasis", ("重点", "划重点", "emphasis")),
        ("teacher_ppt", ("ppt", "课件", "slides")),
        ("homework", ("作业", "homework")),
        ("course_notes", ("笔记", "notes")),
        ("textbook", ("教材", "textbook")),
        ("crash_course", ("冲刺", "速成", "crash")),
    )
    return next((kind for kind, words in rules if any(word in name for word in words)), "course_notes")


def _clean(text: str) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for raw in text.replace("\x00", "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or line in seen or re.fullmatch(r"[-_=*·•\s]{3,}", line):
            continue
        seen.add(line)
        lines.append(line)
    return "\n".join(lines)


def convert_material(path: str | Path, *, source_type: str = "") -> dict[str, Any]:
    source = Path(path)
    result: dict[str, Any] = {
        "path": str(source),
        "name": source.name,
        "source_type": classify_source(source, source_type),
        "priority": 0,
        "text": "",
        "converter": "none",
        "warnings": [],
    }
    result["priority"] = SOURCE_PRIORITY[result["source_type"]]
    if not source.is_file():
        result["warnings"].append("文件不存在，已跳过")
        return result
    try:
        if source.suffix.lower() in {".txt", ".md", ".csv", ".json"}:
            text = source.read_text(encoding="utf-8", errors="replace")
            result["converter"] = "builtin-text"
        else:
            from markitdown import MarkItDown

            text = MarkItDown().convert(str(source)).text_content
            result["converter"] = "markitdown"
        result["text"] = _clean(text)
        if not result["text"]:
            result["warnings"].append("未提取到可用文本")
    except Exception as exc:  # conversion must degrade instead of aborting a review
        result["warnings"].append(f"转换失败，已跳过：{type(exc).__name__}: {exc}")
    return result


def process_materials(paths: list[str | Path], source_types: dict[str, str] | None = None) -> list[dict[str, Any]]:
    source_types = source_types or {}
    materials = [convert_material(path, source_type=source_types.get(str(path), "")) for path in paths]
    return sorted(materials, key=lambda item: (-item["priority"], item["name"]))
