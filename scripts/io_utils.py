"""统一 JSON I/O 与 CLI 包装。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

VERSION = "2.5.1"


def result(
    module: str,
    data: Any | None = None,
    *,
    ok: bool = True,
    warnings: Sequence[Any] | None = None,
    errors: Sequence[Any] | None = None,
    fallback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": ok,
        "data": {} if data is None else data,
        "warnings": list(warnings or []),
        "errors": list(errors or []),
        "meta": {"module": module, "version": VERSION},
    }
    if fallback is not None:
        payload["fallback"] = dict(fallback)
    return payload


def error(code: str, message: str, **details: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "message": message}
    if details:
        item["details"] = details
    return item


def read_json(path: str | Path | None = None) -> Any:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    text = sys.stdin.read()
    if not text.strip():
        raise ValueError("缺少 JSON 输入：请使用 --input 文件或 stdin。")
    return json.loads(text)


def write_json(payload: Any, path: str | Path | None = None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
    if path:
        Path(path).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")


def run_cli(module: str, handler: Callable[[Any], Any]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    try:
        raw = read_json(args.input)
        value = handler(raw)
        payload = value if isinstance(value, dict) and "ok" in value else result(module, value)
        write_json(payload)
        return 0 if payload.get("ok") else 2
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"{module}: {exc}", file=sys.stderr)
        write_json(result(module, ok=False, errors=[error("INVALID_INPUT", str(exc))]))
        return 2
    except OSError as exc:
        print(f"{module}: {exc}", file=sys.stderr)
        write_json(result(module, ok=False, errors=[error("IO_ERROR", str(exc))]))
        return 3
