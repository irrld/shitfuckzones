var ZONES = __ZONES_CONFIG__;
var GAP = __GAP_CONFIG__;
var anchorPos = null;

function applyGap(rect) {
    var half = Math.round(GAP / 2);
    return {
        x: rect.x + half,
        y: rect.y + half,
        width: rect.width - GAP,
        height: rect.height - GAP
    };
}

function findZoneAtCursor(window) {
    var pos = workspace.cursorPos;
    var area = workspace.clientArea(KWin.MaximizeArea, window);

    for (var i = 0; i < ZONES.length; i++) {
        var zone = ZONES[i];
        var zx = area.x + zone.x * area.width;
        var zy = area.y + zone.y * area.height;
        var zw = zone.width * area.width;
        var zh = zone.height * area.height;

        if (pos.x >= zx && pos.x < zx + zw &&
            pos.y >= zy && pos.y < zy + zh) {
            return {
                x: Math.round(zx),
                y: Math.round(zy),
                width: Math.round(zw),
                height: Math.round(zh)
            };
        }
    }
    return null;
}

function findSpanZone(window, anchor) {
    var cp = workspace.cursorPos;
    var pos = {x: cp.x, y: cp.y};
    var area = workspace.clientArea(KWin.MaximizeArea, window);

    var rx1 = Math.min(anchor.x, pos.x);
    var ry1 = Math.min(anchor.y, pos.y);
    var rx2 = Math.max(anchor.x, pos.x);
    var ry2 = Math.max(anchor.y, pos.y);

    var minX = Infinity, minY = Infinity;
    var maxX = -Infinity, maxY = -Infinity;
    var found = false;

    for (var i = 0; i < ZONES.length; i++) {
        var zone = ZONES[i];
        var zx = area.x + zone.x * area.width;
        var zy = area.y + zone.y * area.height;
        var zw = zone.width * area.width;
        var zh = zone.height * area.height;
        var zx2 = zx + zw;
        var zy2 = zy + zh;

        if (rx1 < zx2 && rx2 > zx && ry1 < zy2 && ry2 > zy) {
            found = true;
            if (zx < minX) minX = zx;
            if (zy < minY) minY = zy;
            if (zx2 > maxX) maxX = zx2;
            if (zy2 > maxY) maxY = zy2;
        }
    }

    if (found) {
        return {
            x: Math.round(minX),
            y: Math.round(minY),
            width: Math.round(maxX - minX),
            height: Math.round(maxY - minY)
        };
    }
    return null;
}

function snapWindowToZone(window) {
    var zone = findZoneAtCursor(window);
    if (zone) {
        window.frameGeometry = applyGap(zone);
    }
}

function snapWindowToSpan(window, anchor) {
    var zone = findSpanZone(window, anchor);
    if (zone) {
        window.frameGeometry = applyGap(zone);
    }
}

function connectWindow(window) {
    window.interactiveMoveResizeStarted.connect(function () {
        anchorPos = null;
        var area = workspace.clientArea(KWin.MaximizeArea, window);
        callDBus("org.kde.shitfuckzones", "/KeyMonitor",
                 "org.kde.shitfuckzones.KeyMonitor", "dragStart",
                 Math.round(area.x), Math.round(area.y),
                 Math.round(area.width), Math.round(area.height));
    });

    window.interactiveMoveResizeStepped.connect(function () {
        var cp = workspace.cursorPos;
        callDBus("org.kde.shitfuckzones", "/KeyMonitor",
                 "org.kde.shitfuckzones.KeyMonitor", "updateCursor",
                 Math.round(cp.x), Math.round(cp.y));

        if (anchorPos === null) {
            callDBus("org.kde.shitfuckzones", "/KeyMonitor",
                     "org.kde.shitfuckzones.KeyMonitor", "getModifiers",
                     function (mods) {
                         var ctrl = (mods & 1) !== 0;
                         var shift = (mods & 2) !== 0;
                         if (ctrl && shift && anchorPos === null) {
                             var p = workspace.cursorPos;
                             anchorPos = {x: p.x, y: p.y};
                         }
                     });
        }
    });

    window.interactiveMoveResizeFinished.connect(function () {
        callDBus("org.kde.shitfuckzones", "/KeyMonitor",
                 "org.kde.shitfuckzones.KeyMonitor", "dragEnd");
        callDBus("org.kde.shitfuckzones", "/KeyMonitor",
                 "org.kde.shitfuckzones.KeyMonitor", "getModifiers",
                 function (mods) {
                     var ctrl = (mods & 1) !== 0;
                     var shift = (mods & 2) !== 0;
                     if (ctrl && shift && anchorPos !== null) {
                         snapWindowToSpan(window, anchorPos);
                     } else if (ctrl) {
                         snapWindowToZone(window);
                     }
                     anchorPos = null;
                 });
    });
}

var clients = workspace.stackingOrder;
for (var i = 0; i < clients.length; i++) {
    connectWindow(clients[i]);
}

workspace.windowAdded.connect(function (window) {
    connectWindow(window);
});
