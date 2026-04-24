#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

cd "$ROOT_DIR"

if [ ! -d "$ROOT_DIR/.venv" ]; then
  python3 -m venv .venv
fi

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt

echo "Ambiente virtual pronto em $ROOT_DIR/.venv"
