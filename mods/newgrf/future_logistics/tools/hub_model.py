#!/usr/bin/env python3
# GPL-2.0-only. The Distribution Centre drawn in code, in the same chunky pixel style as the spaceport and Hyperloop.
#
# A 4x4 warehouse with company-colour cladding stands in the facility's north corner. Along its two front faces, the
# south-west and the south-east, runs a row of four truck bays each: eight bays with room for two lorries apiece, so
# sixteen vehicles load at once. World units: x runs down-left, y down-right, z up; 16 units to a tile.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from isorender import Material, Scene  # noqa: E402

T = 16
WALL = Material((206, 208, 210), grain=0.05, tones=5)
RIB = Material((176, 180, 184), grain=0.04)
ROOF = Material((150, 154, 156), grain=0.08)
ROOF_D = Material((120, 124, 126), grain=0.08)
CC = Material((128, 128, 128), company=True)  # company colour: grey, recoloured by the mask
CC_D = Material((96, 96, 96), company=True)
DOOR = Material((70, 74, 80), grain=0.03)
DOOR_SLAT = Material((96, 100, 106), grain=0.03)
DOCK = Material((40, 42, 46), grain=0.02)
BUMPER = Material((236, 180, 30), grain=0.02)
GLASS = Material((96, 150, 180), grain=0.02)
SOLAR = Material((40, 56, 92), grain=0.02)
SOLAR_LINE = Material((120, 140, 170), grain=0.02)
HVAC = Material((184, 186, 188), grain=0.06)
CONCRETE = Material((168, 170, 168), grain=0.12)
APRON = Material((150, 152, 150), grain=0.12)
LINE = Material((240, 220, 90), grain=0.02)
WHITE_LINE = Material((228, 228, 224), grain=0.02)
LIGHT = Material((255, 220, 120), glow=True)

HEIGHT = 36  # warehouse wall height


HAZARD = Material((236, 186, 40), grain=0.02)
HAZARD_D = Material((40, 40, 44), grain=0.02)
PAD = Material((70, 74, 80), grain=0.05)
PAD_RING = Material((240, 200, 60), grain=0.02)
TOWER_GLASS = Material((70, 120, 160), grain=0.03)
TOWER_FRAME = Material((210, 214, 218), grain=0.04)
WINDOW_LIT = Material((255, 230, 150), glow=True)
ARCH = Material((176, 182, 188), grain=0.06, tones=6)
SKY = Material((150, 200, 225), grain=0.03)
LOGO = Material((240, 240, 236), grain=0.02)


def arch_roof(s, x0, x1, y0, y1, z):
    """A barrel-vaulted roof section running along x, with a skylight strip along its crown."""
    w = (y1 - y0) / 2
    c = (y0 + y1) / 2
    prof = [(-w, 0), (-w * 0.92, 2.2), (-w * 0.7, 4.2), (-w * 0.38, 5.6), (0, 6.1), (w * 0.38, 5.6), (w * 0.7, 4.2), (w * 0.92, 2.2), (w, 0)]
    s.prism("x", x0, x1, (c, z), prof, ARCH)
    s.box(x0 + 1, c - 1.2, z + 6.0, x1 - 1, c + 1.2, z + 6.5, SKY)


def drone_pad(s, cx, cy, z):
    s.box(cx - 5, cy - 5, z, cx + 5, cy + 5, z + 1.5, PAD)
    for k in range(12):  # a ring of yellow marks
        import math
        a = k * math.pi / 6
        px, py = cx + 3.6 * math.cos(a), cy + 3.6 * math.sin(a)
        s.box(px - 0.5, py - 0.5, z + 1.5, px + 0.5, py + 0.5, z + 1.7, PAD_RING)
    s.box(cx - 0.4, cy - 2, z + 1.5, cx + 0.4, cy + 2, z + 1.7, LOGO)
    s.box(cx - 1.6, cy - 0.4, z + 1.5, cx + 1.6, cy + 0.4, z + 1.7, LOGO)


def warehouse(s):
    """The 4x4 warehouse: an office tower on the back corner, vaulted roofs with drone pads, dock doors on both
    front faces under lit, hazard-striped canopies, and company-colour pilasters and logo panels."""
    x0, y0, x1, y1, h = 1, 1, 4 * T - 1, 4 * T - 1, HEIGHT
    s.box(x0, y0, 0, x1, y1, h, WALL, top=ROOF_D, sides=WALL)
    # Corrugated cladding: vertical ribs between door head and eaves.
    for k in range(1, 24):
        y = y0 + k * (y1 - y0) / 24
        s.box(x1, y - 0.25, 18, x1 + 0.35, y + 0.25, h - 5, RIB)
        x = x0 + k * (x1 - x0) / 24
        s.box(x - 0.25, y1, 18, x + 0.25, y1 + 0.35, h - 5, RIB)
    # Company colour: the eaves band, pilasters at the corners and between bay pairs, and a logo panel per face.
    s.box(x1, y0, h - 5, x1 + 0.6, y1, h, CC)
    s.box(x0, y1, h - 5, x1, y1 + 0.6, h, CC)
    for k in range(5):
        p = min(max(k * T, x0 + 0.5), x1 - 1.5)
        s.box(x1, p, 0, x1 + 1.2, p + 1.4, h, CC_D)
        s.box(p, y1, 0, p + 1.4, y1 + 1.2, h, CC_D)
    s.box(x1 + 0.6, 2 * T - 9, 21, x1 + 1.0, 2 * T + 9, h - 7, CC)
    s.box(2 * T - 9, y1 + 0.6, 21, 2 * T + 9, y1 + 1.0, h - 7, CC)
    # The company's mark on each logo panel: a white arrow pointing out along the face, a parcel on the move.
    for k, wide in enumerate((0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 3.0, 2.2, 1.4, 0.6)):
        u = 2 * T - 7 + k * 1.3
        zc = (21 + h - 7) / 2
        s.box(x1 + 1.0, u, zc - wide, x1 + 1.2, u + 1.3, zc + wide, LOGO)
        s.box(u, y1 + 1.0, zc - wide, u + 1.3, y1 + 1.2, zc + wide, LOGO)
    # Dock doors: two per bay tile on each front face, one for each lorry.
    for i in range(4):
        for off in (4.5, 11.5):
            c = i * T + off
            s.box(x1, c - 2.8, 1, x1 + 0.6, c + 2.8, 13, DOCK)
            s.box(x1 + 0.6, c - 2.4, 1.5, x1 + 0.8, c + 2.4, 12.5, DOOR)
            for z in range(3, 13, 2):
                s.box(x1 + 0.8, c - 2.4, z, x1 + 0.9, c + 2.4, z + 0.5, DOOR_SLAT)
            s.box(x1 + 0.6, c - 3.3, 0, x1 + 1.8, c - 2.7, 2.2, BUMPER)
            s.box(x1 + 0.6, c + 2.7, 0, x1 + 1.8, c + 3.3, 2.2, BUMPER)
            s.box(c - 2.8, y1, 1, c + 2.8, y1 + 0.6, 13, DOCK)
            s.box(c - 2.4, y1 + 0.6, 1.5, c + 2.4, y1 + 0.8, 12.5, DOOR)
            for z in range(3, 13, 2):
                s.box(c - 2.4, y1 + 0.8, z, c + 2.4, y1 + 0.9, z + 0.5, DOOR_SLAT)
            s.box(c - 3.3, y1 + 0.6, 0, c - 2.7, y1 + 1.8, 2.2, BUMPER)
            s.box(c + 2.7, y1 + 0.6, 0, c + 3.3, y1 + 1.8, 2.2, BUMPER)
            # A lamp over each door.
            s.box(x1 + 3.2, c - 0.6, 14.2, x1 + 3.6, c + 0.6, 14.6, LIGHT)
            s.box(c - 0.6, y1 + 3.2, 14.2, c + 0.6, y1 + 3.6, 14.6, LIGHT)
    # One continuous canopy along each face, with a hazard-striped edge.
    s.box(x1, y0, 15, x1 + 4, y1, 16.2, CC_D)
    s.box(x0, y1, 15, x1, y1 + 4, 16.2, CC_D)
    for k in range(0, 4 * T - 2, 2):
        m = HAZARD if (k // 2) % 2 == 0 else HAZARD_D
        s.box(x1 + 4, y0 + k, 15, x1 + 4.3, y0 + k + 2, 16.2, m)
        s.box(x0 + k, y1 + 4, 15, x0 + k + 2, y1 + 4.3, 16.2, m)
    # Roof: parapet, three vaults with skylights, plant, and two drone pads.
    s.box(x0, y0, h, x1, y0 + 0.8, h + 1.5, ROOF_D)
    s.box(x0, y1 - 0.8, h, x1, y1, h + 1.5, ROOF_D)
    s.box(x0, y0, h, x0 + 0.8, y1, h + 1.5, ROOF_D)
    s.box(x1 - 0.8, y0, h, x1, y1, h + 1.5, ROOF_D)
    for k in range(3):
        arch_roof(s, 20, x1 - 2, 18 + k * 14.5, 31 + k * 14.5, h)
    drone_pad(s, 9, 40, h)
    drone_pad(s, 9, 54, h)
    s.box(26, 4, h, 34, 12, h + 4, HVAC)
    s.box(40, 4, h, 48, 12, h + 4, HVAC)
    s.box(54, 4, h, 61, 12, h + 3, HVAC)
    # The office tower on the back corner: glass, white frame, lit floors and a company-colour crown.
    tx0, ty0, tx1, ty1, th = 2, 2, 18, 18, 72
    s.box(tx0, ty0, h, tx1, ty1, th, TOWER_GLASS, top=ROOF_D, sides=TOWER_GLASS)
    for z in range(int(h) + 4, th - 6, 5):
        s.box(tx1, ty0, z, tx1 + 0.4, ty1, z + 0.8, TOWER_FRAME)
        s.box(tx0, ty1, z, tx1, ty1 + 0.4, z + 0.8, TOWER_FRAME)
    for z in range(int(h) + 6, th - 8, 10):
        s.box(tx1 + 0.1, ty0 + 3, z, tx1 + 0.5, ty0 + 8, z + 2, WINDOW_LIT)
        s.box(tx0 + 9, ty1 + 0.1, z + 5, tx0 + 14, ty1 + 0.5, z + 7, WINDOW_LIT)
    s.box(tx0 - 0.5, ty0 - 0.5, th - 6, tx1 + 0.5, ty1 + 0.5, th, CC)
    s.box(tx0 + 4, ty0 + 4, th, tx1 - 4, ty1 - 4, th + 3, ROOF_D)
    s.box(tx1 - 2, ty1 - 2, th + 3, tx1 - 1, ty1 - 1, th + 12, TOWER_FRAME)
    s.box(tx1 - 2.2, ty1 - 2.2, th + 12, tx1 - 0.8, ty1 - 0.8, th + 13, Material((255, 80, 60), glow=True))


def bay(s, ox, oy, axis):
    """A truck bay tile at (ox, oy) in units: concrete apron with markings for two lorries side by side.
    axis 'x': the bay row along the south-west face (lorries back in along x); 'y': along the south-east face."""
    s.quad((ox, oy, 0), (ox + T, oy, 0), (ox + T, oy + T, 0), (ox, oy + T, 0), APRON)
    for off in (0.6, 8, 15.4):  # bay dividers
        if axis == "x":
            s.box(ox + 1, oy + off - 0.35, 0.05, ox + 13, oy + off + 0.35, 0.1, LINE)
        else:
            s.box(ox + off - 0.35, oy + 1, 0.05, ox + off + 0.35, oy + 13, 0.1, LINE)
    for off in (4.5, 11.5):  # stop lines at the dock
        if axis == "x":
            s.box(ox + 1, oy + off - 2, 0.05, ox + 1.6, oy + off + 2, 0.1, WHITE_LINE)
        else:
            s.box(ox + off - 2, oy + 1, 0.05, ox + off + 2, oy + 1.6, 0.1, WHITE_LINE)


def facility():
    """The whole 5x5 facility: the warehouse and its eight bays (the far corner tile is left free)."""
    s = Scene()
    warehouse(s)
    for i in range(4):
        bay(s, 4 * T, i * T, "x")
        bay(s, i * T, 4 * T, "y")
    return s
