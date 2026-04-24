#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Ambiente virtual nao encontrado. Rode scripts/bootstrap.sh primeiro."
  exit 1
fi

cd "$ROOT_DIR"
"$VENV_PYTHON" main.py "$@"
