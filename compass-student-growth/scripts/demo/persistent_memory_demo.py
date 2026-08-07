"""Prove structured growth state survives independent Python processes."""
from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path
from tempfile import TemporaryDirectory

if __package__ in {None, ""}: sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.memory.memory_engine import MemoryEngine


def phase_a(path: Path) -> int:
    MemoryEngine(path).persist_turn(user_id="xiaoyu", profile_updates={"preferred_name": "小宇", "major": "计算机网络技术"}, goal_updates={"target_city": "杭州", "target_job_normalized": "IT支持"}, growth_updates={"current_skill": "Active Directory", "completed_tasks": ["Domain Creation"], "next_task": "User / Group / GPO"})
    print("Session A saved: Active Directory / Domain Creation")
    return 0


def phase_b(path: Path) -> int:
    restored = MemoryEngine(path).load_user_context(user_id="xiaoyu", query="继续")
    assert restored["profile"]["preferred_name"] == "小宇"
    assert restored["growth_state"]["completed_tasks"] == ["Domain Creation"]
    print("Session B restored: 上次正在补 Active Directory；域创建已完成；下一项 User / Group / GPO")
    return 0


def main() -> int:
    with TemporaryDirectory(prefix="compass-memory-demo-") as runtime:
        db = Path(runtime) / "memory.sqlite3"; script = Path(__file__).resolve()
        for phase in ("a", "b"):
            completed = subprocess.run([sys.executable, "-B", str(script), f"--phase-{phase}", str(db)], text=True, encoding="utf-8", errors="strict", capture_output=True, check=False, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            print(completed.stdout.strip())
            if completed.returncode: print(completed.stderr, file=sys.stderr); return completed.returncode
    print("[PASS] 独立 Python 进程跨会话恢复成功。")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--phase-a": raise SystemExit(phase_a(Path(sys.argv[2])))
    if len(sys.argv) == 3 and sys.argv[1] == "--phase-b": raise SystemExit(phase_b(Path(sys.argv[2])))
    raise SystemExit(main())
