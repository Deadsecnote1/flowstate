#!/usr/bin/env bash
# Install Supabase sync deps (venv preferred; PEP 668 fallback on Ubuntu).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"
REQ="$ROOT/requirements-sync.txt"

install_in_venv() {
  if ! python3 -m venv "$VENV" 2>/dev/null; then
    rm -rf "$VENV"
    return 1
  fi
  "$VENV/bin/python" -m pip install -U pip
  "$VENV/bin/python" -m pip install -r "$REQ"
  echo ""
  echo "Installed in $VENV"
  echo "Run with sync: $ROOT/scripts/run-flowstate.sh"
}

install_break_system() {
  echo "Using pip --break-system-packages (system Python)."
  python3 -m pip install --user --break-system-packages -r "$REQ"
  echo ""
  echo "Run with sync: PYTHONPATH=$ROOT/src python3 -m flowstate"
}

if install_in_venv; then
  :
elif install_break_system; then
  :
else
  echo "Could not install sync dependencies."
  echo ""
  echo "Option A (recommended): install venv support, then re-run this script:"
  echo "  sudo apt install python3.12-venv"
  echo "  ./scripts/install-sync-deps.sh"
  echo ""
  echo "Option B: allow pip on system Python:"
  echo "  python3 -m pip install --user --break-system-packages -r requirements-sync.txt"
  exit 1
fi

echo ""
echo "Config: ~/.config/io.github.Deadsecnote1.Flowstate/sync.env"
echo "Guide:  $ROOT/docs/SYNC_SETUP.md"
