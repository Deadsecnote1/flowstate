#!/usr/bin/env bash
# Run Flowstate from source with optional .venv sync dependencies.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  exec "$ROOT/.venv/bin/python" -m flowstate "$@"
fi

exec python3 -m flowstate "$@"
