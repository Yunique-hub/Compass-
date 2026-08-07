"""Cross-platform developer bootstrap with explicit checks and no global writes."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, required: bool = True) -> dict[str, object]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    item = {"command": command, "exit_code": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}
    if required and completed.returncode:
        raise RuntimeError(json.dumps(item, ensure_ascii=False))
    return item


def main(install: bool) -> int:
    report: dict[str, object] = {
        "python": sys.version.split()[0],
        "node": shutil.which("node"),
        "pnpm": shutil.which("pnpm"),
        "git": shutil.which("git"),
        "install_requested": install,
        "checks": [],
    }
    if sys.version_info < (3, 10):
        raise RuntimeError("Compass 需要 Python >= 3.10")
    if install:
        local_uv = ROOT / ".tooling" / "uv" / "bin" / ("uv.exe" if sys.platform == "win32" else "uv")
        uv = shutil.which("uv") or str(local_uv)
        if not Path(uv).exists() and not shutil.which("uv"):
            raise RuntimeError("未找到 uv；请安装 uv，或将可执行文件放到 .tooling/uv/uv.exe")
        report["checks"].append(run([uv, "sync", "--extra", "dev"]))  # type: ignore[index]
        if shutil.which("pnpm"):
            report["checks"].append(run(["pnpm", "install", "--frozen-lockfile"]))  # type: ignore[index]
    report["checks"].append(run([sys.executable, "-B", "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"]))  # type: ignore[index]
    report["checks"].append(run([sys.executable, "scripts/validate_package.py"]))  # type: ignore[index]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="同步 Python 与 Node 依赖；默认仅验证")
    args = parser.parse_args()
    raise SystemExit(main(args.install))
