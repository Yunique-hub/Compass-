#!/usr/bin/env python3
"""Validate an ezAgent ZIP package with one skill-name root directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath


def yaml_value(text: str, field: str) -> str | None:
    match = re.search(rf"^{re.escape(field)}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def validate(zip_path: Path, skill_name: str, version: str) -> dict:
    errors: list[str] = []
    with zipfile.ZipFile(zip_path) as archive:
        files = [info for info in archive.infolist() if not info.is_dir()]
        names = [info.filename.replace("\\", "/") for info in files]

        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", name):
                errors.append(f"unsafe path: {name}")

        if len(names) != len(set(names)):
            errors.append("duplicate paths")
        if len(names) != len({name.casefold() for name in names}):
            errors.append("case-insensitive path collision")

        roots = sorted({PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts})
        if roots != [skill_name]:
            errors.append(f"expected one root '{skill_name}', got {roots}")

        required = {
            f"{skill_name}/SKILL.md",
            f"{skill_name}/manifest.yaml",
            f"{skill_name}/agents/openai.yaml",
        }
        missing = sorted(required - set(names))
        if missing:
            errors.append(f"missing required files: {missing}")

        forbidden = {
            f"{skill_name}/README.md",
            f"{skill_name}/scripts/build_release.py",
            f"{skill_name}/scripts/validate_platform_package.py",
        }
        development_files = sorted(
            name
            for name in names
            if name in forbidden
            or name.startswith(f"{skill_name}/docs/")
            or name.startswith(f"{skill_name}/tests/")
            or "/__pycache__/" in name
        )
        if development_files:
            errors.append(f"development-only files in release: {development_files}")

        manifest_name = manifest_version = None
        manifest_path = f"{skill_name}/manifest.yaml"
        if manifest_path in names:
            manifest = archive.read(manifest_path).decode("utf-8-sig")
            manifest_name = yaml_value(manifest, "name")
            manifest_version = yaml_value(manifest, "version")
            if manifest_name != skill_name:
                errors.append(f"manifest name is {manifest_name!r}")
            if manifest_version != version:
                errors.append(f"manifest version is {manifest_version!r}")
            if yaml_value(manifest, "scope") != "private":
                errors.append("manifest scope must be 'private'")

        skill_path = f"{skill_name}/SKILL.md"
        if skill_path in names:
            skill_text = archive.read(skill_path).decode("utf-8-sig")
            frontmatter = re.match(r"^---\r?\n(.*?)\r?\n---", skill_text, re.DOTALL)
            if not frontmatter or yaml_value(frontmatter.group(1), "name") != skill_name:
                errors.append("SKILL.md frontmatter name mismatch")
            elif not yaml_value(frontmatter.group(1), "description"):
                errors.append("SKILL.md frontmatter description is missing")

        agents_path = f"{skill_name}/agents/openai.yaml"
        if agents_path in names:
            agents_text = archive.read(agents_path).decode("utf-8-sig")
            if f"${skill_name}" not in agents_text:
                errors.append("agents/openai.yaml default_prompt must mention the skill")

        return {
            "valid": not errors,
            "skill_name": skill_name,
            "version": version,
            "file_count": len(files),
            "total_uncompressed_bytes": sum(info.file_size for info in files),
            "zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest().upper(),
            "errors": errors,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an ezAgent skill ZIP")
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        result = validate(args.zip_path, args.skill_name, args.version)
    except (OSError, UnicodeError, zipfile.BadZipFile) as exc:
        result = {
            "valid": False,
            "skill_name": args.skill_name,
            "version": args.version,
            "errors": [str(exc)],
        }
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
