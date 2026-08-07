"""Read-only public web policy for agent-browser."""
from __future__ import annotations

from urllib.parse import urlparse

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
BLOCKED_SCHEMES = {"file", "ftp", "data", "javascript"}
WRITE_COMMANDS = {"click", "fill", "type", "press", "upload", "check", "uncheck", "select", "drag", "eval"}
READ_COMMANDS = {"open", "get", "snapshot", "find", "close"}


def validate_public_url(url: str, allowed_domains: set[str] | None = None) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme.casefold() != "https" or parsed.scheme.casefold() in BLOCKED_SCHEMES:
        raise PermissionError("RESEARCH_HTTPS_ONLY")
    if not host or host in BLOCKED_HOSTS or host.endswith(".local"):
        raise PermissionError("RESEARCH_NON_PUBLIC_HOST")
    if allowed_domains and not any(host == domain or host.endswith("." + domain) for domain in allowed_domains):
        raise PermissionError("RESEARCH_DOMAIN_NOT_ALLOWED")
    return host


def validate_command(command: str) -> None:
    head = command.strip().split(maxsplit=1)[0].casefold()
    if head in WRITE_COMMANDS or head not in READ_COMMANDS:
        raise PermissionError("RESEARCH_READ_ONLY")
