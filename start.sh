#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo '请先运行 ./scripts/setup.sh 安装本项目依赖。'
  exit 1
fi
exec .venv/bin/python desktop/main.py "$@"
