#!/usr/bin/env sh
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_ROOT"
if [ ! -x .venv/bin/python ]; then
  echo "未找到 .venv。请先运行：python scripts/bootstrap_dev.py --install" >&2
  exit 2
fi
.venv/bin/python scripts/bootstrap_dev.py
