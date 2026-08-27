#!/usr/bin/env bash
# Install desktop entry and icons for the current user (no sudo).
# Uses PNG icons + absolute Icon= path so Cinnamon/Mint menus show the icon.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP_ID="io.github.Deadsecnote1.Flowstate"

DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
ICON_PNG_48="$ICON_DIR/48x48/apps/${APP_ID}.png"

mkdir -p "$DESKTOP_DIR"

# Ensure hicolor theme index exists (needed for icon lookup)
if [[ ! -f "$ICON_DIR/index.theme" ]]; then
  mkdir -p "$ICON_DIR"
  cat > "$ICON_DIR/index.theme" <<'EOF'
[Icon Theme]
Name=Hicolor
Comment=Fallback icon theme
Directories=16x16/apps,24x24/apps,32x32/apps,48x48/apps,64x64/apps,128x128/apps,256x256/apps,scalable/apps,symbolic/apps
Hidden=true
Example=folder

[16x16/apps]
Size=16
Context=Applications
Type=Fixed

[24x24/apps]
Size=24
Context=Applications
Type=Fixed

[32x32/apps]
Size=32
Context=Applications
Type=Fixed

[48x48/apps]
Size=48
Context=Applications
Type=Fixed

[64x64/apps]
Size=64
Context=Applications
Type=Fixed

[128x128/apps]
Size=128
Context=Applications
Type=Fixed

[256x256/apps]
Size=256
Context=Applications
Type=Fixed

[scalable/apps]
Size=128
Context=Applications
Type=Scalable
MinSize=1
MaxSize=512

[symbolic/apps]
Size=16
Context=Applications
Type=Scalable
MinSize=1
MaxSize=512
EOF
fi

# Install PNG sizes (Cinnamon prefers these over SVG-only)
for size in 16 24 32 48 64 128 256; do
  mkdir -p "$ICON_DIR/${size}x${size}/apps"
  install -m 644 "$ROOT/data/icons/hicolor/${size}x${size}/apps/${APP_ID}.png" \
    "$ICON_DIR/${size}x${size}/apps/${APP_ID}.png"
done

mkdir -p "$ICON_DIR/scalable/apps" "$ICON_DIR/symbolic/apps"
install -m 644 "$ROOT/data/icons/hicolor/scalable/apps/${APP_ID}.svg" \
  "$ICON_DIR/scalable/apps/${APP_ID}.svg"
install -m 644 "$ROOT/data/icons/hicolor/symbolic/apps/${APP_ID}-symbolic.svg" \
  "$ICON_DIR/symbolic/apps/${APP_ID}-symbolic.svg"

# Absolute Icon path is the most reliable on Cinnamon/Mint
cat > "$DESKTOP_DIR/${APP_ID}.desktop" <<EOF
[Desktop Entry]
Name=Flowstate
GenericName=Task list
Comment=Tasks, planner, and clock for your desktop
Exec="${ROOT}/flowstate"
Path=${ROOT}
Icon=${ICON_PNG_48}
Terminal=false
Type=Application
Categories=Utility;
Keywords=flowstate;tasks;tasks;checklist;reminders;
StartupNotify=true
EOF

chmod 644 "$DESKTOP_DIR/${APP_ID}.desktop"

# Refresh caches
rm -f "$ICON_DIR/icon-theme.cache" 2>/dev/null || true
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$ICON_DIR" >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

# Ask Cinnamon to reload the menu if possible
if command -v dbus-send >/dev/null 2>&1; then
  dbus-send --session --dest=org.Cinnamon --type=method_call \
    /org/Cinnamon org.Cinnamon.Eval string:'Main.panel.menuManager._menus.forEach(function(m){});' \
    >/dev/null 2>&1 || true
fi

echo "Installed menu entry: $DESKTOP_DIR/${APP_ID}.desktop"
echo "Icon file: $ICON_PNG_48"
echo
echo "Open the app menu and search for: Flowstate"
echo "If the icon still looks blank, press Alt+F2, type r, press Enter (restarts Cinnamon)."
