#!/usr/bin/env python3
import json
import os
import signal
import sys
import threading

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

import evdev
from evdev import ecodes

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont


def load_config():
    user_config = os.path.expanduser('~/.config/shitfuckzones/config.json')
    if os.path.isfile(user_config):
        path = user_config
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    with open(path) as f:
        config = json.load(f)
    active = config['active_layout']
    return config['layouts'][active]['zones'], config['appearance']


class Signals(QObject):
    show_overlay = pyqtSignal(int, int, int, int)
    hide_overlay = pyqtSignal()
    update_highlight = pyqtSignal(int, int, int, int)


class OverlayWindow(QWidget):
    def __init__(self, zones, appearance):
        super().__init__()
        self.zones = zones
        self.appearance = appearance
        self.area_origin = (0, 0)
        self._cursor = None
        self._anchor = None
        self._prev_highlighted = frozenset()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.Tool
            | Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def show_at(self, x, y, w, h):
        self.area_origin = (x, y)
        self.setGeometry(x, y, w, h)
        self.show()
        self.update()

    def set_highlight(self, cx, cy, ax, ay):
        self._cursor = (cx, cy)
        self._anchor = (ax, ay) if ax >= 0 else None
        new_highlighted = self._calc_highlighted()
        if new_highlighted != self._prev_highlighted:
            self._prev_highlighted = new_highlighted
            self.update()

    def hideEvent(self, event):
        self._cursor = None
        self._anchor = None
        self._prev_highlighted = frozenset()
        super().hideEvent(event)

    def _calc_highlighted(self):
        if self._cursor is None:
            return frozenset()

        w, h = self.width(), self.height()
        ox, oy = self.area_origin
        cx, cy = self._cursor[0] - ox, self._cursor[1] - oy
        highlighted = set()

        if self._anchor:
            anx, any_ = self._anchor[0] - ox, self._anchor[1] - oy
            rx1, rx2 = min(cx, anx), max(cx, anx)
            ry1, ry2 = min(cy, any_), max(cy, any_)
            for i, zone in enumerate(self.zones):
                zx = zone['x'] * w
                zy = zone['y'] * h
                zx2 = zx + zone['width'] * w
                zy2 = zy + zone['height'] * h
                if rx1 < zx2 and rx2 > zx and ry1 < zy2 and ry2 > zy:
                    highlighted.add(i)
        else:
            for i, zone in enumerate(self.zones):
                zx = zone['x'] * w
                zy = zone['y'] * h
                if (cx >= zx and cx < zx + zone['width'] * w and
                        cy >= zy and cy < zy + zone['height'] * h):
                    highlighted.add(i)
                    break

        return frozenset(highlighted)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        gap = self.appearance['zone_gap']
        half_gap = gap / 2
        radius = self.appearance.get('zone_border_radius', 0)

        zone_color = QColor(self.appearance['zone_color'])
        zone_color.setAlphaF(self.appearance['zone_opacity'])
        highlight_color = QColor(self.appearance['zone_highlight_color'])
        highlight_color.setAlphaF(self.appearance['zone_highlight_opacity'])
        border_color = QColor(self.appearance['zone_border_color'])
        border_width = self.appearance['zone_border_width']

        highlighted = self._prev_highlighted
        pen = QPen(border_color, border_width)
        painter.setPen(pen)

        font_size = self.appearance.get('zone_number_font_size', 16)
        font = QFont()
        font.setPixelSize(font_size)
        font.setBold(True)

        for i, zone in enumerate(self.zones):
            rect = QRectF(
                zone['x'] * w + half_gap,
                zone['y'] * h + half_gap,
                zone['width'] * w - gap,
                zone['height'] * h - gap,
            )
            fill = highlight_color if i in highlighted else zone_color
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, radius, radius)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        number_color = QColor(self.appearance.get('zone_number_color', '#ffffff'))
        painter.setFont(font)
        painter.setPen(QPen(number_color))
        for i, zone in enumerate(self.zones):
            rect = QRectF(
                zone['x'] * w + half_gap,
                zone['y'] * h + half_gap,
                zone['width'] * w - gap,
                zone['height'] * h - gap,
            )
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(i + 1))

        painter.end()


class KeyMonitor(dbus.service.Object):
    def __init__(self, bus_name, signals_obj):
        super().__init__(bus_name, '/KeyMonitor')
        self.ctrl_held = False
        self.shift_held = False
        self.dragging = False
        self.signals = signals_obj
        self.work_area = None
        self.last_cursor = (0, 0)
        self.anchor = None

    def _emit_highlight(self):
        ax, ay = self.anchor if self.anchor else (-1, -1)
        cx, cy = self.last_cursor
        self.signals.update_highlight.emit(cx, cy, ax, ay)

    def update_overlay(self):
        if self.dragging and self.ctrl_held and self.work_area:
            if self.shift_held and self.anchor is None:
                self.anchor = self.last_cursor
            elif not self.shift_held:
                self.anchor = None
            x, y, w, h = self.work_area
            self.signals.show_overlay.emit(x, y, w, h)
            self._emit_highlight()
        else:
            self.anchor = None
            self.signals.hide_overlay.emit()

    @dbus.service.method('org.kde.shitfuckzones.KeyMonitor',
                         in_signature='', out_signature='i')
    def getModifiers(self):
        mods = 0
        if self.ctrl_held:
            mods |= 1
        if self.shift_held:
            mods |= 2
        return mods

    @dbus.service.method('org.kde.shitfuckzones.KeyMonitor',
                         in_signature='iiii', out_signature='')
    def dragStart(self, x, y, w, h):
        self.dragging = True
        self.work_area = (x, y, w, h)
        self.anchor = None
        self.update_overlay()

    @dbus.service.method('org.kde.shitfuckzones.KeyMonitor',
                         in_signature='', out_signature='')
    def dragEnd(self):
        self.dragging = False
        self.anchor = None
        self.update_overlay()

    @dbus.service.method('org.kde.shitfuckzones.KeyMonitor',
                         in_signature='ii', out_signature='')
    def updateCursor(self, x, y):
        self.last_cursor = (x, y)
        if self.dragging and self.ctrl_held and self.work_area:
            self._emit_highlight()

    def find_keyboards(self):
        keyboards = []
        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)
            caps = dev.capabilities()
            if ecodes.EV_KEY in caps:
                keys = caps[ecodes.EV_KEY]
                if ecodes.KEY_LEFTCTRL in keys and ecodes.KEY_A in keys:
                    keyboards.append(dev)
        if not keyboards:
            raise RuntimeError("No keyboard device found")
        return keyboards

    def start_monitoring(self):
        keyboards = self.find_keyboards()

        def reader(dev):
            for event in dev.read_loop():
                if event.type == ecodes.EV_KEY:
                    changed = False
                    if event.code in (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL):
                        self.ctrl_held = event.value > 0
                        changed = True
                    elif event.code in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT):
                        self.shift_held = event.value > 0
                        changed = True
                    if changed:
                        self.update_overlay()

        for dev in keyboards:
            t = threading.Thread(target=reader, args=(dev,), daemon=True)
            t.start()


def main():
    zones, appearance = load_config()
    app = QApplication(sys.argv)
    signals = Signals()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    bus_name = dbus.service.BusName('org.kde.shitfuckzones', bus,
                                    allow_replacement=True,
                                    replace_existing=True,
                                    do_not_queue=True)

    monitor = KeyMonitor(bus_name, signals)
    monitor.start_monitoring()

    glib_loop = GLib.MainLoop()
    threading.Thread(target=glib_loop.run, daemon=True).start()

    overlay = OverlayWindow(zones, appearance)
    signals.show_overlay.connect(overlay.show_at)
    signals.hide_overlay.connect(overlay.hide)
    signals.update_highlight.connect(overlay.set_highlight)

    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
