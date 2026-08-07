"""Read-only Agent Browser boundary for public recruitment evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.research.browser_policy import validate_command, validate_public_url
from scripts.research.research_engine import ResearchEngine


class AgentBrowserAdapter:
    def __init__(self, *, project_root: str | Path | None = None, reader: Any | None = None) -> None:
        self.root = Path(project_root or Path(__file__).resolve().parents[2]); self.reader = reader

    def health(self) -> dict[str, Any]:
        cli = self.root / "node_modules" / "agent-browser" / "bin" / "agent-browser.js"
        return {"provider": "agent_browser", "available": self.reader is not None or cli.is_file(), "read_only": True, "upstream": "vercel-labs/agent-browser"}

    def execute(self, command: str) -> Any:
        validate_command(command)
        if self.reader is None: raise RuntimeError("AGENT_BROWSER_READER_UNAVAILABLE")
        return self.reader(command)

    def read_public_page(self, url: str) -> dict[str, Any]:
        host = validate_public_url(url)
        if self.reader is not None:
            output = self.execute(f"get text {url}"); content = output.get("content", "") if isinstance(output, dict) else str(output)
            return {"ok": bool(content), "source_url": url, "host": host, "content": content, "collected_at": datetime.now(timezone.utc).isoformat(), "mode": "agent-browser-read-only"}
        output = ResearchEngine(project_root=self.root, allowed_domains={host}).read_page(url)
        return {**output, "source_url": url, "collected_at": datetime.now(timezone.utc).isoformat()}


__all__ = ["AgentBrowserAdapter", "ResearchEngine"]
