#!/bin/bash
set -e

SCRIPT_NAME="shitfuckzones"
DEST="$HOME/.local/share/kwin/scripts/$SCRIPT_NAME"
SRC="$(cd "$(dirname "$0")" && pwd)"
AUTOSTART="$HOME/.config/autostart/${SCRIPT_NAME}-daemon.desktop"

kill_daemon() {
    pkill -f "python3.*$SCRIPT_NAME/daemon.py" 2>/dev/null || true
    sleep 0.3
}

uninstall() {
    echo "Uninstalling $SCRIPT_NAME..."
    kill_daemon
    kwriteconfig6 --file kwinrc --group Plugins --key "${SCRIPT_NAME}Enabled" false
    qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "$SCRIPT_NAME" 2>/dev/null || true
    qdbus6 org.kde.KWin /KWin reconfigure
    rm -rf "$DEST"
    rm -f "$AUTOSTART"
    echo "Done."
    exit 0
}

if [ "$1" = "--uninstall" ]; then
    uninstall
fi

# Remove old install if present
if [ -d "$DEST" ]; then
    rm -rf "$DEST"
fi

# Embed config into KWin script
mkdir -p "$DEST/contents/code"
cp "$SRC/metadata.json" "$DEST/"
python3 -c "
import json
with open('$SRC/config.json') as f:
    config = json.load(f)
active = config['active_layout']
zones = json.dumps(config['layouts'][active]['zones'])
gap = config['appearance']['zone_gap']
with open('$SRC/contents/code/main.js') as f:
    js = f.read()
js = js.replace('__ZONES_CONFIG__', zones)
js = js.replace('__GAP_CONFIG__', str(gap))
with open('$DEST/contents/code/main.js', 'w') as f:
    f.write(js)
"

# Enable and reload KWin script
kwriteconfig6 --file kwinrc --group Plugins --key "${SCRIPT_NAME}Enabled" true
qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "$SCRIPT_NAME" 2>/dev/null || true
qdbus6 org.kde.KWin /KWin reconfigure
qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.start

# Restart daemon
kill_daemon
python3 "$SRC/daemon.py" &
disown

# Set up autostart
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=shitfuckzones daemon
Exec=python3 $SRC/daemon.py
X-GNOME-Autostart-enabled=true
X-KDE-autostart-phase=2
EOF

echo "Installed. Daemon running (PID $!), autostart configured."
