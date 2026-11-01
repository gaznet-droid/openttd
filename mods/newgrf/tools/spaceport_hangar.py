#!/usr/bin/env python3
# GPL-2.0-only. The spaceport's tall assembly hangar, drawn in code and laid over the pad art. Needs NumPy and Pillow.
#
# The handoff pad has a low hangar in its left-hand (west) corner. At rocket scale it read as too small, so it is
# replaced by an assembly building about as tall as the Starship. It stands on the same corner tile, which is the
# spaceport's hangar tile in the game (src/future_logistics/orbital.cpp), so clicking it opens the depot.
# World units: x runs down-left, y down-right, z up, measured from the pad's north corner; 16 units to a tile.
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from isorender import Scene, Material  # noqa: E402

# The low hangar's ground area in the pad art (measured), which the new building covers completely.
X0, X1, Y0, Y1 = 30.5, 47.5, 1.5, 21.0
HEIGHT = 112  # about the docked Starship's height (139 px including the launch mount)

WALL = Material((196, 199, 202), grain=0.06, tones=5)
WALL_SHADE = Material((168, 172, 176), grain=0.06, tones=5)
RIB = Material((150, 154, 160), grain=0.04)
ROOF = Material((178, 180, 180), grain=0.08)
STRIPE = Material((236, 170, 40), grain=0.05)
DOOR = Material((52, 58, 68), grain=0.03)
DOOR_PANEL = Material((70, 78, 90), grain=0.03)
HAZARD = Material((232, 186, 40), grain=0.02)
GLASS = Material((96, 140, 170), grain=0.02)
BASE = Material((120, 122, 122), grain=0.10)
LIGHT = Material((255, 120, 90), glow=True)


def hangar_scene():
    s = Scene()
    x0, x1, y0, y1, h = X0, X1, Y0, Y1, HEIGHT
    # Plinth and main block.
    s.box(x0 - 0.5, y0 - 0.5, 0, x1 + 0.5, y1 + 0.5, 2, BASE)
    s.box(x0, y0, 2, x1, y1, h, WALL, top=ROOF, sides=WALL)
    # Vertical ribs on the two visible faces (the +x face looks down-left, the +y face down-right).
    for k in range(1, 6):
        y = y0 + k * (y1 - y0) / 6
        s.box(x1, y - 0.35, 2, x1 + 0.45, y + 0.35, h - 1, RIB)
    for k in range(1, 5):
        x = x0 + k * (x1 - x0) / 5
        if abs(x - (x0 + x1) / 2) < 4.5:
            continue  # leave the door clear
        s.box(x - 0.35, y1, 2, x + 0.35, y1 + 0.45, h - 1, RIB)
    # Horizontal band of windows high on the +x face.
    s.box(x1 + 0.05, y0 + 1.5, h - 14, x1 + 0.35, y1 - 1.5, h - 10, GLASS)
    # The tall door on the face towards the launch mount (+y), with a hazard-striped frame.
    cx = (x0 + x1) / 2
    s.box(cx - 5.2, y1 + 0.05, 2, cx + 5.2, y1 + 0.5, h - 18, HAZARD)
    s.box(cx - 4.4, y1 + 0.5, 2, cx + 4.4, y1 + 0.75, h - 20, DOOR)
    for k in range(1, 6):
        z = 2 + k * (h - 22) / 6
        s.box(cx - 4.4, y1 + 0.75, z - 0.4, cx + 4.4, y1 + 0.85, z + 0.4, DOOR_PANEL)
    # Roof: the yellow stripes of the original hangar, and a parapet.
    for k in range(3):
        x = x0 + 3 + k * 5
        s.box(x, y0 + 1.5, h, x + 2.2, y1 - 1.5, h + 0.4, STRIPE)
    s.box(x0, y0, h, x1, y0 + 0.6, h + 1.2, WALL_SHADE)
    s.box(x0, y1 - 0.6, h, x1, y1, h + 1.2, WALL_SHADE)
    s.box(x0, y0, h, x0 + 0.6, y1, h + 1.2, WALL_SHADE)
    s.box(x1 - 0.6, y0, h, x1, y1, h + 1.2, WALL_SHADE)
    # Red aircraft-warning lights on the top corners.
    for x, y in ((x1 - 1, y0 + 1), (x1 - 1, y1 - 1), (x0 + 1, y1 - 1)):
        s.box(x - 0.5, y - 0.5, h + 1.2, x + 0.5, y + 0.5, h + 2.2, LIGHT)
    return s


def overlay(grid, zoom, north):
    """Draw the hangar onto a pad picture in game pixels; north is the footprint's north corner in that picture."""
    img, _, (ox, oy) = hangar_scene().render(zoom=zoom)
    out = grid.copy()
    left, top = north[0] + ox, north[1] + oy
    if left < 0 or top < 0:
        # Grow the canvas so the tall building is not cut off; the caller re-anchors with the returned shift.
        pad_x, pad_y = max(0, -left), max(0, -top)
        bigger = Image.new("RGBA", (out.width + pad_x, out.height + pad_y))
        bigger.alpha_composite(out, (pad_x, pad_y))
        out = bigger
        left, top = left + pad_x, top + pad_y
        bigger.alpha_composite(img, (left, top))
        return bigger, (pad_x, pad_y)
    out.alpha_composite(img, (left, top))
    return out, (0, 0)
