"""Synchronize pinned upstream repositories into trackable vendor snapshots.

Git repositories live in ``runtime/cache/upstream``.  The ``vendor`` tree is
an exported source snapshot without nested ``.git`` directories, so the outer
Compass repository and the full distribution contain the real source files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "reference" / "open_source" / "upstream-lock.json"
CACHE_ROOT = ROOT / "runtime" / "cache" / "upstream"
VENDOR_ROOT = ROOT / "vendor"
MARKER_NAME = ".upstream-source.json"


class VendorSyncError(RuntimeError):
    """Raised when a vendor snapshot cannot be updated safely."""


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise VendorSyncError(f"command failed ({completed.returncode}): {detail}")
    return completed.stdout.strip()


def _git(repository: Path, *arguments: str) -> str:
    return _run(
        [
            "git",
            "-c",
            f"safe.directory={repository.resolve()}",
            "-C",
            str(repository),
            *arguments,
        ]
    )


def load_lock(path: Path = LOCK_PATH) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    projects = payload.get("projects")
    if not isinstance(projects, dict) or not projects:
        raise VendorSyncError("upstream lock has no projects")
    return projects


def clone_or_update(
    repository: str,
    destination: Path,
    commit: str,
    *,
    offline: bool = False,
) -> str:
    """Clone or update a cache checkout and detach it at one pinned commit."""

    if destination.exists() and not (destination / ".git").is_dir():
        raise VendorSyncError(f"refusing non-Git cache destination: {destination}")

    if not destination.exists():
        if offline:
            raise VendorSyncError(f"offline cache is missing: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", "--filter=blob:none", "--no-checkout", repository, str(destination)])

    if _git(destination, "status", "--porcelain"):
        raise VendorSyncError(f"cache checkout is dirty: {destination}")
    if _git(destination, "remote", "get-url", "origin") != repository:
        raise VendorSyncError(f"cache remote mismatch: {destination}")

    if not offline:
        _git(destination, "fetch", "--depth", "1", "origin", commit)
    _git(destination, "checkout", "--detach", commit)
    actual = _git(destination, "rev-parse", "HEAD")
    if actual != commit:
        raise VendorSyncError(f"commit mismatch for {destination}: {actual}")
    return actual


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or ".git" in path.parts or path.name == MARKER_NAME:
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _verify_snapshot(destination: Path) -> None:
    marker_path = destination / MARKER_NAME
    if not marker_path.is_file():
        raise VendorSyncError(f"vendor snapshot has no ownership marker: {destination}")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    actual = tree_digest(destination)
    if marker.get("tree_sha256") != actual:
        raise VendorSyncError(
            f"vendor snapshot was modified; refusing overwrite: {destination}"
        )


def _copy_snapshot(source: Path, destination: Path, metadata: dict[str, Any]) -> None:
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".git"),
    )
    marker = {
        "repository": metadata["repository"],
        "branch": metadata["branch"],
        "commit": metadata["commit"],
        "tree_sha256": tree_digest(destination),
    }
    (destination / MARKER_NAME).write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_snapshot(source: Path, destination: Path, metadata: dict[str, Any]) -> None:
    """Replace an unchanged managed snapshot with an export from ``source``."""

    if destination.exists():
        _verify_snapshot(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(f".{destination.name}.previous")
    try:
        if backup.exists():
            raise VendorSyncError(f"stale vendor backup requires review: {backup}")
        if destination.exists():
            destination.rename(backup)
        destination.mkdir(parents=True, exist_ok=False)
        _copy_snapshot(source, destination, metadata)
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if destination.exists():
            shutil.rmtree(destination)
        if backup.exists():
            backup.rename(destination)
        raise


def adopt_existing_repository(
    destination: Path,
    cache: Path,
    metadata: dict[str, Any],
) -> None:
    """Turn an initial clean vendor clone into cache plus managed snapshot."""

    if not (destination / ".git").is_dir() or cache.exists():
        return
    if _git(destination, "status", "--porcelain"):
        raise VendorSyncError(f"initial vendor clone is dirty: {destination}")
    if _git(destination, "rev-parse", "HEAD") != metadata["commit"]:
        raise VendorSyncError(f"initial vendor commit mismatch: {destination}")
    if _git(destination, "remote", "get-url", "origin") != metadata["repository"]:
        raise VendorSyncError(f"initial vendor remote mismatch: {destination}")

    cache.parent.mkdir(parents=True, exist_ok=True)
    destination.rename(cache)
    try:
        destination.mkdir(parents=True, exist_ok=False)
        _copy_snapshot(cache, destination, metadata)
    except Exception:
        if destination.exists():
            shutil.rmtree(destination)
        if cache.exists():
            cache.rename(destination)
        raise


def synchronize(*, offline: bool, adopt_existing: bool) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for name, metadata in load_lock().items():
        vendor = VENDOR_ROOT / name
        cache = CACHE_ROOT / name
        if adopt_existing:
            adopt_existing_repository(vendor, cache, metadata)
        commit = clone_or_update(
            metadata["repository"], cache, metadata["commit"], offline=offline
        )
        export_snapshot(cache, vendor, metadata)
        results.append({"project": name, "commit": commit, "status": "synced"})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="do not fetch from remotes")
    parser.add_argument(
        "--adopt-existing",
        action="store_true",
        help="convert clean initial vendor clones into managed snapshots",
    )
    args = parser.parse_args()
    try:
        results = synchronize(offline=args.offline, adopt_existing=args.adopt_existing)
    except (OSError, ValueError, VendorSyncError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "projects": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
