#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
SXF_UV="$(command -v uv || true)"
if [[ -z "$SXF_UV" && -x "$HOME/.local/bin/uv" ]]; then SXF_UV="$HOME/.local/bin/uv"; fi
if [[ -z "$SXF_UV" ]]; then echo '请安装 uv: https://docs.astral.sh/uv/getting-started/installation/'; exit 1; fi
"$SXF_UV" venv --python 3.12 .venv
"$SXF_UV" pip install --python .venv/bin/python -r backend/requirements.lock -r desktop/requirements.lock
echo '依赖已安装。运行 ./start.sh 打开原生桌面窗口。'
