#!/bin/bash
set -e

SCRIPT_NAME="shitfuckzones"
SRC="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
DEST="$HOME/.local/share/kwin/scripts/$SCRIPT_NAME"
AUTOSTART="$HOME/.config/autostart/${SCRIPT_NAME}-daemon.desktop"
USER_CONFIG_DIR="$HOME/.config/$SCRIPT_NAME"
USER_CONFIG="$USER_CONFIG_DIR/config.json"
UDEV_RULE_SYSTEM="/etc/udev/rules.d/99-${SCRIPT_NAME}.rules"
UDEV_RULE_PKG="/usr/lib/udev/rules.d/99-${SCRIPT_NAME}.rules"

if [[ "$SRC" == /usr/* ]]; then
    DAEMON_EXEC="/usr/bin/${SCRIPT_NAME}-daemon"
else
    DAEMON_EXEC="python3 $SRC/daemon.py"
fi

kill_daemon() {
    pkill -f "python3.*$SCRIPT_NAME.*daemon.py" 2>/dev/null || true
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
    if [ -f "$UDEV_RULE_SYSTEM" ]; then
        echo "Removing udev rule at $UDEV_RULE_SYSTEM (requires sudo)..."
        sudo rm -f "$UDEV_RULE_SYSTEM"
        sudo udevadm control --reload 2>/dev/null || true
    fi
    echo "Done."
    exit 0
}

has_input_access() {
    python3 - <<'PY' 2>/dev/null
import evdev, sys
devs = evdev.list_devices()
if not devs:
    sys.exit(1)
for p in devs:
    try:
        evdev.InputDevice(p)
        sys.exit(0)
    except PermissionError:
        continue
sys.exit(1)
PY
}

ensure_input_access() {
    if has_input_access; then
        return 0
    fi
    if [ ! -f "$UDEV_RULE_PKG" ] && [ ! -f "$UDEV_RULE_SYSTEM" ]; then
        echo "Need read access to /dev/input/event* for keyboard detection."
        echo "Installing udev rule at $UDEV_RULE_SYSTEM (requires sudo)..."
        sudo install -Dm644 "$SRC/udev/99-${SCRIPT_NAME}.rules" "$UDEV_RULE_SYSTEM"
    fi
    sudo udevadm control --reload
    sudo udevadm trigger --subsystem-match=input --action=change
    sudo setfacl -m "u:$USER:r" /dev/input/event* 2>/dev/null || true
    if ! has_input_access; then
        echo "Warning: still can't read /dev/input/event*. A re-login or reboot may be needed."
    fi
}

if [ "$1" = "--uninstall" ]; then
    uninstall
fi

ensure_input_access

# Bootstrap user config from default on first run
if [ ! -f "$USER_CONFIG" ]; then
    mkdir -p "$USER_CONFIG_DIR"
    cp "$SRC/config.json" "$USER_CONFIG"
    echo "Created $USER_CONFIG — edit to customize layouts."
fi

# Remove old install if present
if [ -d "$DEST" ]; then
    rm -rf "$DEST"
fi

# Embed user config into KWin script
mkdir -p "$DEST/contents/code"
cp "$SRC/metadata.json" "$DEST/"
python3 -c "
import json
with open('$USER_CONFIG') as f:
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
$DAEMON_EXEC &
disown

# Set up autostart
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=shitfuckzones daemon
Exec=$DAEMON_EXEC
X-GNOME-Autostart-enabled=true
X-KDE-autostart-phase=2
EOF

echo "Installed. Daemon running (PID $!), autostart configured."
