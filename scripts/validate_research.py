#!/usr/bin/env python3
"""Validate time-sensitive Compass claims before publication."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_input(argument: str | None) -> dict[str, Any]:
    raw = Path(argument).read_text(encoding="utf-8") if argument and argument != "-" else sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    return data


def valid_https_urls(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(url, str) and urlparse(url).scheme == "https" and bool(urlparse(url).netloc)
        for url in value
    )


def valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not DATE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate(data: dict[str, Any]) -> dict[str, Any]:
    claims = data.get("claims", [])
    if not isinstance(claims, list):
        return {"publishable": False, "errors": ["claims must be a list"], "claims": []}
    results: list[dict[str, Any]] = []
    for index, claim in enumerate(claims):
        errors: list[str] = []
        if not isinstance(claim, dict):
            results.append({"index": index, "publishable": False, "errors": ["claim must be an object"]})
            continue
        if not str(claim.get("text", "")).strip():
            errors.append("text is required")
        time_sensitive = claim.get("time_sensitive", False) is True
        kind = claim.get("claim_kind", "general")
        if time_sensitive:
            if not valid_https_urls(claim.get("source_urls")):
                errors.append("time-sensitive claim requires at least one valid HTTPS source URL")
            checked_at = claim.get("checked_at") or claim.get("collection_end")
            if not valid_date(checked_at):
                errors.append("time-sensitive claim requires checked_at or collection_end in YYYY-MM-DD")
        if kind == "market_summary":
            for field in ("region", "role_scope"):
                if not str(claim.get(field, "")).strip():
                    errors.append(f"market_summary requires {field}")
            sample_count = claim.get("sample_count")
            if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count <= 0:
                errors.append("market_summary requires positive integer sample_count")
            for field in ("collection_start", "collection_end"):
                value = claim.get(field)
                if not valid_date(value):
                    errors.append(f"market_summary requires {field} in YYYY-MM-DD")
            start = claim.get("collection_start")
            end = claim.get("collection_end")
            if valid_date(start) and valid_date(end) and date.fromisoformat(start) > date.fromisoformat(end):
                errors.append("market_summary collection_start must not be after collection_end")
            limitations = claim.get("limitations")
            if not isinstance(limitations, list) or not any(str(item).strip() for item in limitations):
                errors.append("market_summary requires at least one limitation")
            urls = claim.get("source_urls")
            if isinstance(urls, list) and len(urls) != len(set(urls)):
                errors.append("market_summary source_urls must be deduplicated")
        if kind == "single_jd" and claim.get("market_generalization") is True:
            errors.append("single_jd cannot be generalized to the market")
        results.append({"index": index, "publishable": not errors, "errors": errors})
    errors = [f"claim[{item['index']}]: {error}" for item in results for error in item["errors"]]
    return {"publishable": not errors, "errors": errors, "claims": results}


def main() -> int:
    try:
        result = validate(load_input(sys.argv[1] if len(sys.argv) > 1 else None))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"publishable": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["publishable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
