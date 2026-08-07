"""Explicit, bounded and auditable agent-browser research with snapshot fallback."""
from __future__ import annotations

import subprocess
import shlex
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .browser_policy import validate_command, validate_public_url


class ResearchEngine:
    def __init__(self, *, project_root: str | Path, allowed_domains: set[str] | None = None, timeout: int = 30) -> None:
        self.root = Path(project_root)
        self.allowed_domains = allowed_domains
        self.timeout = timeout

    def read_page(self, url: str, *, selector: str = "body") -> dict[str, Any]:
        host = validate_public_url(url, self.allowed_domains)
        commands = [f"open {url}", f"get text {selector}", "close"]
        for command in commands:
            validate_command(command)
        try:
            node = shutil.which("node")
            cli = self.root / "node_modules" / "agent-browser" / "bin" / "agent-browser.js"
            if not node or not cli.is_file():
                raise RuntimeError("agent-browser CLI 未安装")
            outputs = []
            opened = False
            for command in commands:
                completed = subprocess.run(
                    [node, str(cli), *shlex.split(command)], cwd=self.root,
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=self.timeout, check=False,
                )
                if completed.returncode:
                    raise RuntimeError(completed.stderr.strip() or f"agent-browser exit {completed.returncode}")
                opened = opened or command.startswith("open ")
                outputs.append(completed.stdout.strip())
            return {"ok": True, "url": url, "host": host, "content": outputs[1], "collected_at": datetime.now(timezone.utc).isoformat(), "mode": "public-readonly"}
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            if locals().get("opened") and locals().get("node") and locals().get("cli"):
                subprocess.run([node, str(cli), "close"], cwd=self.root, capture_output=True, timeout=5, check=False)
            return {"ok": False, "url": url, "host": host, "content": "", "mode": "offline-snapshot-required", "warning": f"公开网页读取失败：{type(exc).__name__}: {exc}"}
