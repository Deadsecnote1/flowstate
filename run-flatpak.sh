#!/usr/bin/env bash
# Run Todo using the GNOME Flatpak runtime when system GTK4 GIR packages
# are not installed (common on minimal Debian/Ubuntu setups).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# Prefer a widely available GNOME runtime; override via env if needed.
RUNTIME_VERSION="${TODO_FLATPAK_RUNTIME:-47}"
if ! flatpak info "org.gnome.Platform//${RUNTIME_VERSION}" &>/dev/null; then
  for candidate in 50 49 48 47 46; do
    if flatpak info "org.gnome.Platform//${candidate}" &>/dev/null; then
      RUNTIME_VERSION="$candidate"
      break
    fi
  done
fi

exec flatpak run \
  --filesystem="${ROOT}:ro" \
  --filesystem=xdg-data/io.github.thanushiyan.Todo:create \
  --share=ipc \
  --socket=session-bus \
  --socket=fallback-x11 \
  --socket=wayland \
  --device=dri \
  --talk-name=org.freedesktop.Notifications \
  --command=bash \
  "org.gnome.Platform//${RUNTIME_VERSION}" \
  -c "cd \"${ROOT}\" && PYTHONPATH=src python3 -m todo"
