"""Build and validate Compass skill, dev and full release archives."""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from typing import Any

try:
    from .io_utils import result, write_json
    from .validate_package import DEV_FILES, FORBIDDEN_PARTS, FORBIDDEN_SUFFIXES, MODES, ROOT, validate_directory, validate_zip
except ImportError:
    from io_utils import result, write_json
    from validate_package import DEV_FILES, FORBIDDEN_PARTS, FORBIDDEN_SUFFIXES, MODES, ROOT, validate_directory, validate_zip

MODULE = "pack_skill"
SKILL_TOP_LEVEL = {"SKILL.md", "manifest.yaml", "pyproject.toml", "uv.lock", "LICENSE", "THIRD_PARTY_NOTICES.md", "config", "licenses", "reference", "scripts", "agents"}
SKILL_SCRIPT_EXCLUSIONS = {"bootstrap_dev.py", "demo_pipeline.py", "demo_v2.py", "pack_skill.py", "validate_package.py", "vendor_sync.py"}
DEV_TOP_LEVEL_EXCLUSIONS = {"compass-student-growth"}


def should_include(path: Path, output: Path, mode: str) -> bool:
    relative = path.relative_to(ROOT)
    if path.resolve() == output.resolve() or any(part in FORBIDDEN_PARTS for part in relative.parts):
        return False
    if path.suffix in FORBIDDEN_SUFFIXES or relative.parts[0] in DEV_TOP_LEVEL_EXCLUSIONS:
        return False
    if mode == "skill":
        if relative.parts[0] not in SKILL_TOP_LEVEL:
            return False
        if relative.parts[0] == "scripts" and (relative.name in SKILL_SCRIPT_EXCLUSIONS or "demo" in relative.parts):
            return False
    if mode != "full" and relative.parts[0] == "vendor":
        return False
    return True


def pack(output: Path, *, mode: str = "skill") -> dict[str, Any]:
    if mode not in MODES:
        return result(MODULE, ok=False, errors=[{"code": "INVALID_MODE", "message": mode}])
    directory_check = validate_directory(ROOT, mode=mode)
    if not directory_check["ok"]:
        return result(MODULE, ok=False, errors=directory_check["errors"], warnings=directory_check["warnings"])
    output = output if output.is_absolute() else ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and should_include(path, output, mode):
                archive.write(path, path.relative_to(ROOT).as_posix())
    zip_check = validate_zip(output, mode=mode)
    return result(MODULE, {"output": str(output), "mode": mode, "size_bytes": output.stat().st_size, "directory_validation": directory_check["data"], "zip_validation": zip_check["data"]}, ok=zip_check["ok"], warnings=directory_check["warnings"] + zip_check["warnings"], errors=zip_check["errors"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=sorted(MODES), default="skill")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    version = __import__("scripts.archive_v2", fromlist=["VERSION"]).VERSION
    output = args.output or Path(f"dist/compass-student-growth-{version}-{args.mode}.zip")
    payload = pack(output, mode=args.mode)
    write_json(payload)
    raise SystemExit(0 if payload["ok"] else 2)
