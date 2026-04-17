# shitfuckzones

A FancyZones clone for KDE Plasma 6 that actually fucking works.

## Why does this exist?

Because every other window tiling/zone tool on Linux either:
- Shit itself on a 32:9 super ultrawide and had a *minimum zone size*. A minimum. Size. For zones. What the fuck?
- Had no way to span a window across multiple zones, which is the entire goddamn point of zones
- Offered no option to disable auto tiling - cool thanks I just wanted zones, not for you to rearrange my entire desktop every time I open a terminal
- Hadn't been updated since Plasma 5 was cool
- Was "almost done" since 2019

Could some of this be a skill issue? Absolutely. But at some point you stop reading documentation and start writing angry code. This is that code.

## What does it do?

PowerToys FancyZones, but on Linux. That's it. That's the pitch.

- **Ctrl + drag** a window and release - it snaps to the zone under your cursor
- **Ctrl + Shift + drag** - span across multiple zones (anchor where Shift was pressed, bounding box of all intersecting zones on release)
- A semi-transparent overlay shows the zone grid while you drag
- The highlighted zone updates live as you move the cursor
- Fully configurable layouts and appearance via `config.json`

## Requirements

- KDE Plasma 6 (Wayland)
- Python 3 with: `PyQt6`, `dbus-python`, `python-evdev`, `PyGObject`
- Read access to `/dev/input/event*` — `install.sh` will prompt for `sudo` once to drop a udev rule (`TAG+="uaccess"`) that grants the active seat user ACL access, then apply it immediately with `udevadm trigger` + `setfacl`.

## Install

```bash
./install.sh
```

This does everything: installs the KWin script, embeds your layout config, starts the daemon, and sets up autostart on login.

## Uninstall

```bash
./install.sh --uninstall
```

Gone. No traces. Like it never happened. Except for this repo on your disk, staring at you.

## Configuration

Edit `config.json` and re-run `./install.sh`. Layouts use proportional coordinates (0.0–1.0) relative to the usable screen area.

Several layouts are included:
- `my-grid` - 24-zone grid (my personal setup for 32:9 super ultrawide monitor)
- `halves` - left/right split
- `thirds` - three columns
- `grid-2x2` - four quadrants
- `main-side` - large main area + two stacked side panels
- `priority-grid` - narrow/wide/narrow columns

Set `active_layout` to whichever you want. Appearance (colors, opacity, gap, border) is also configurable.

## Architecture

Two components, because KWin scripts can render windows but not overlays:

1. **KWin Script** (`contents/code/main.js`) - hooks into window drag events, handles zone calculation and snapping, talks to the daemon via DBus.
2. **Daemon** (`daemon.py`) - monitors keyboard via evdev (for Ctrl/Shift detection), renders the zone overlay via PyQt6, communicates with the KWin script over DBus.

## License

MIT. Do whatever you want with it. Name your fork something worse, I dare you.
