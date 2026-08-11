#!/usr/bin/env python3
"""Build the runtime-only ezAgent ZIP with deterministic file metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path


SKILL_NAME = "compass-student-growth"
RUNTIME_FILES = (
    "SKILL.md",
    "manifest.yaml",
    "agents/openai.yaml",
    "references/academic-context.md",
    "references/career-research-resources.md",
    "references/domain-intelligence.md",
    "references/examples.md",
    "references/execution-contracts.md",
    "references/final-review.md",
    "references/goals-planning.md",
    "references/persistent-memory.md",
    "references/response-safety.md",
    "references/tutor-assessment.md",
    "scripts/validate_plan.py",
    "scripts/validate_research.py",
    "scripts/validate_response.py",
)


def manifest_version(root: Path) -> str:
    text = (root / "manifest.yaml").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(\d+\.\d+\.\d+)\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError("manifest.yaml has no semantic version")
    return match.group(1)


def build(root: Path, version: str, output: Path) -> dict:
    actual = manifest_version(root)
    if actual != version:
        raise ValueError(f"manifest version is {actual}, expected {version}")

    missing = [name for name in RUNTIME_FILES if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing runtime files: {missing}")

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in RUNTIME_FILES:
            data = (root / name).read_bytes()
            info = zipfile.ZipInfo(f"{SKILL_NAME}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    digest = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    return {
        "skill_name": SKILL_NAME,
        "version": version,
        "file_count": len(RUNTIME_FILES),
        "zip_path": str(output),
        "zip_bytes": output.stat().st_size,
        "zip_sha256": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Compass ezAgent release ZIP")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output = args.output or root / f"{SKILL_NAME}-{args.version}.zip"
    try:
        result = build(root, args.version, output)
        compatibility = root / "skill.zip"
        shutil.copyfile(output, compatibility)
        result["compatibility_path"] = str(compatibility)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"built": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    result["built"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
