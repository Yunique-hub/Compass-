"""创建根目录无额外套层的可上传 zip，并立即复验内容。"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from typing import Any

try:
    from .io_utils import result, write_json
    from .validate_package import validate_directory, validate_zip
except ImportError:
    from io_utils import result, write_json
    from validate_package import validate_directory, validate_zip

MODULE = "pack_skill"
ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git", "__pycache__", ".pytest_cache", ".test-deps", ".venv", "venv",
    ".tooling", "node_modules", ".agent-browser", ".pnpm-store", ".pycache",
}


def should_include(path: Path, output: Path, mode: str) -> bool:
    relative = path.relative_to(ROOT)
    if path.resolve() == output.resolve() or any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.suffix in {".pyc", ".db", ".sqlite", ".sqlite3", ".tmp"}:
        return False
    if relative.parts and relative.parts[0] == "runtime":
        return False
    if mode == "skill" and relative.parts and relative.parts[0] == "vendor":
        return False
    if relative.parts and relative.parts[0] == "dist" and path.suffix == ".zip":
        return False
    return True


def pack(output: Path, *, mode: str = "skill") -> dict[str, Any]:
    if mode not in {"skill", "full"}:
        return result(MODULE, ok=False, errors=[{"code": "INVALID_MODE", "message": mode}])
    directory_check = validate_directory(ROOT)
    if not directory_check["ok"]:
        return result(MODULE, ok=False, errors=directory_check["errors"], warnings=directory_check["warnings"])
    output = output if output.is_absolute() else ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and should_include(path, output, mode):
                archive.write(path, path.relative_to(ROOT).as_posix())
    zip_check = validate_zip(output)
    return result(MODULE, {"output": str(output), "mode": mode, "size_bytes": output.stat().st_size, "directory_validation": directory_check["data"], "zip_validation": zip_check["data"]}, ok=zip_check["ok"], warnings=directory_check["warnings"] + zip_check["warnings"], errors=zip_check["errors"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("skill", "full"), default="skill")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path(f"dist/compass-student-growth-2.0.0-{args.mode}.zip")
    payload = pack(output, mode=args.mode)
    write_json(payload)
    raise SystemExit(0 if payload["ok"] else 2)
