#!/usr/bin/env python3
# GPL-2.0-only. Draws every Hyperloop sprite in code and writes them into the Future Logistics NewGRF.
#
#   python3 mods/newgrf/future_logistics/tools/hyperloop/make_hyperloop_art.py
#
# Needs NumPy, Pillow and NML (for the palette of the company-colour masks). Everything is drawn with
# ../../../tools/isorender.py at OpenTTD's own projection and pixel size, so the pieces line up on the map:
# world units are 1/16 of a tile, a height level is 8 units, and a sprite's offsets are measured from the
# world point the game anchors it to (a tile's north corner for ground sprites, a bounding-box origin for
# buildings, the vehicle's position for vehicles).
#
# Sprites written, each at normal and 2x zoom:
#   track      underlay (16) and overlay (16) in the RailTrackOffset order
#   viaduct    deck surfaces (6) followed by the viaduct's structure (20): see VIADUCT_ORDER
#   tube       portal ground (4) and portal hood (4), by tunnel direction NE, SE, SW, NW
#   depot      six building sprites in the base game's depot order
#   gui        eight toolbar icons and eight cursors
#   terminal   station platforms and canopy, back and front, for the X and Y axes
#   pods       propulsion pod, passenger capsule and mail capsule, eight directions each
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
FL = HERE.parents[1]
sys.path.insert(0, str(FL.parent / "tools"))
from isorender import Material, Scene  # noqa: E402
from nml.palette import raw_palette_data  # noqa: E402

GFX = FL / "gfx" / "hyperloop"
T = 16
LEVEL = 8

# --- materials -------------------------------------------------------------------------------------------------
WHITE = Material((214, 218, 222))
PANEL = Material((178, 186, 194))
ROOF = Material((200, 206, 212))
DARK = Material((26, 30, 40), grain=0.02)
SLOT = Material((40, 46, 56), grain=0.02)
GLASS = Material((90, 150, 175))
CONCRETE = Material((178, 180, 178), grain=0.12)
CONCRETE_D = Material((138, 140, 140), grain=0.12)
PLATFORM = Material((196, 198, 194), grain=0.10)
EDGE = Material((236, 196, 40))
CYAN = Material((90, 240, 255), glow=True)
CC = Material((128, 128, 128), company=True)  # company colour: grey here, recoloured by the mask
WIN = Material((20, 26, 40), grain=0.02)
GLAZE = Material((120, 196, 220), grain=0.03)
CANOPY_GLASS = Material((150, 210, 228), grain=0.03)


def project(p, zoom):
    x, y, z = p
    return 2 * zoom * (y - x), zoom * (x + y) - zoom * z


def finish(scene, zoom, anchor, overlays=()):
    """Render a scene; overlays are (scene, opacity) drawn translucently on top. Returns (rgba, mask, xrel, yrel)."""
    img, mask, (ox, oy) = scene.render(zoom=zoom)
    for over, opacity in overlays:
        if not over.tris:
            continue
        oi, om, (o2x, o2y) = over.render(zoom=zoom, outline=0.85, crease=1.0)
        # Grow the canvas to hold both.
        left, top = min(ox, o2x), min(oy, o2y)
        right, bottom = max(ox + img.width, o2x + oi.width), max(oy + img.height, o2y + oi.height)
        canvas = Image.new("RGBA", (right - left, bottom - top))
        canvas.alpha_composite(img, (ox - left, oy - top))
        cm = Image.new("L", canvas.size)
        cm.paste(mask, (ox - left, oy - top))
        a = np.asarray(oi).astype(float)
        a[..., 3] *= opacity
        canvas.alpha_composite(Image.fromarray(a.astype(np.uint8)), (o2x - left, o2y - top))
        img, mask, ox, oy = canvas, cm, left, top
    ax, ay = project(anchor, zoom)
    box = img.getbbox() or (0, 0, 1, 1)
    img, mask = img.crop(box), mask.crop(box)
    return img, mask, int(round(ox + box[0] - ax)), int(round(oy + box[1] - ay))


def empty():
    return Image.new("RGBA", (1, 1)), Image.new("L", (1, 1)), 0, 0


# --- building blocks -------------------------------------------------------------------------------------------
def guideway(s, p0, p1, z_at=None, bed=True, z=0.0):
    """The guideway beam between two ground points: concrete bed, beam, two glowing magnetic rails, centre slot."""
    if bed:
        s.beam(p0, p1, 6, z, z + 1, CONCRETE_D, z_at=z_at)
    s.beam(p0, p1, 4, z + 1, z + 3, CONCRETE, z_at=z_at)
    s.beam(p0, p1, 0.5, z + 3, z + 3.4, CYAN, z_at=z_at, top=CYAN) if False else None
    for off in (-2.7, 2.7):
        (x0, y0), (x1, y1) = p0, p1
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln * off, dx / ln * off
        s.beam((x0 + nx, y0 + ny), (x1 + nx, y1 + ny), 0.5, z + 3, z + 3.4, CYAN, z_at=z_at)
    s.beam(p0, p1, 1, z + 3, z + 3.2, SLOT, z_at=z_at)


# Track pieces in tile coordinates: (start, end) on the ground.
X_PIECE = ((0, 8), (16, 8))
Y_PIECE = ((8, 0), (8, 16))
N_PIECE = ((0, 8), (8, 0))
S_PIECE = ((16, 8), (8, 16))
E_PIECE = ((0, 8), (8, 16))
W_PIECE = ((8, 0), (16, 8))
SLOPES = {  # RTO_SLOPE_NE, SE, SW, NW: piece and the height across the tile
    "NE": (X_PIECE, lambda x, y: LEVEL * (T - x) / T),
    "SE": (Y_PIECE, lambda x, y: LEVEL * y / T),
    "SW": (X_PIECE, lambda x, y: LEVEL * x / T),
    "NW": (Y_PIECE, lambda x, y: LEVEL * (T - y) / T),
}


def track_sprites(zoom, overlay):
    """Sixteen sprites in RailTrackOffset order: X, Y, N, S, E, W, slopes NE..NW, crossing, junctions SW, NE, SE, NW, NSEW."""
    out = []
    pieces = [X_PIECE, Y_PIECE, N_PIECE, S_PIECE, E_PIECE, W_PIECE]
    for p in pieces:
        s = Scene()
        guideway(s, *p, bed=not overlay)
        out.append(finish(s, zoom, (0, 0, 0)))
    for key in ("NE", "SE", "SW", "NW"):
        piece, z_at = SLOPES[key]
        s = Scene()
        guideway(s, *piece, z_at=z_at, bed=not overlay)
        out.append(finish(s, zoom, (0, 0, 0)))
    if overlay:
        out += [empty() for _ in range(6)]
        return out
    s = Scene()  # crossing
    s.quad((1, 1, 0), (15, 1, 0), (15, 15, 0), (1, 15, 0), CONCRETE_D)
    guideway(s, *X_PIECE, bed=False)
    guideway(s, *Y_PIECE, bed=False)
    out.append(finish(s, zoom, (0, 0, 0)))
    for _ in range(5):  # junction beds: the overlay adds the beams
        s = Scene()
        s.quad((1, 1, 0), (15, 1, 0), (15, 15, 0), (1, 15, 0), CONCRETE_D)
        s.quad((3, 3, 0.4), (13, 3, 0.4), (13, 13, 0.4), (3, 13, 0.4), CONCRETE)
        out.append(finish(s, zoom, (0, 0, 0)))
    return out


# --- viaduct ---------------------------------------------------------------------------------------------------
R = 5.0  # tube radius
TUBE_Z = 4.2  # tube centre above the deck
OCT = [(R * math.cos(math.pi / 8 + i * math.pi / 4), R * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)]
BRIDGE_Z_START = 3


def tube_faces(axis, front):
    """The tube's faces, split into the half behind the vehicle (front=False) and the half in front of it."""
    solid, glass = Scene(), Scene()
    c = 8
    for i in range(8):
        (u0, z0), (u1, z1) = OCT[i], OCT[(i + 1) % 8]
        um = (u0 + u1) / 2
        # u is across the tube: towards +y for an X-axis tube, +x for a Y-axis tube. Larger u is nearer the camera.
        is_front = um > 0.5
        if is_front != front:
            continue
        if front and i in (7, 0):
            target, m = glass, GLAZE
        else:
            target, m = solid, (WHITE if i in (1, 2, 3) else PANEL)
        def P(t, u, z):
            return (t, c + u, TUBE_Z + z) if axis == "x" else (c + u, t, TUBE_Z + z)
        target.quad(P(0, u0, z0), P(T, u0, z0), P(T, u1, z1), P(0, u1, z1), m)
    if front:  # cyan running light along the lower front edge
        def P(t, u, z):
            return (t, c + u, TUBE_Z + z) if axis == "x" else (c + u, t, TUBE_Z + z)
        u, zz = R * 0.72, -R * 0.70
        solid.quad(P(0, u, zz), P(T, u, zz), P(T, u + 0.4, zz + 0.4), P(0, u + 0.4, zz + 0.4), CYAN)
    # collar ring at the middle of the tile, split the same way
    for i in range(8):
        (u0, z0), (u1, z1) = OCT[i], OCT[(i + 1) % 8]
        if ((u0 + u1) / 2 > 0.5) != front:
            continue
        k = 1.12
        def P(t, u, z):
            return (t, c + u, TUBE_Z + z) if axis == "x" else (c + u, t, TUBE_Z + z)
        solid.quad(P(7.4, u0 * k, z0 * k), P(8.6, u0 * k, z0 * k), P(8.6, u1 * k, z1 * k), P(7.4, u1 * k, z1 * k), WHITE)
    return solid, glass


def deck_and_cradle(axis):
    """Behind the vehicle: the deck slab under the guideway and the Y cradle that carries the tube."""
    s = Scene()
    def B(u0, u1, t0, t1, z0, z1, m):
        if axis == "x":
            s.box(t0, 8 + u0, z0, t1, 8 + u1, z1, m)
        else:
            s.box(8 + u0, t0, z0, 8 + u1, t1, z1, m)
    B(-5.2, 5.2, 0, T, -1.2, 0, PANEL)
    B(-3.6, 3.6, 7.2, 8.8, -3.0, -1.2, WHITE)  # cradle under the collar
    return s


def viaduct_structure(zoom):
    """Floor (behind), roof (in front) and pillar for the X and then Y axis, then the eight heads."""
    out = []
    for axis in ("x", "y"):
        back_solid, _ = tube_faces(axis, front=False)
        floor = deck_and_cradle(axis)
        floor.tris += back_solid.tris
        # The floor is anchored at the tile's north corner, BRIDGE_Z_START below the deck.
        out.append(finish(floor, zoom, (0, 0, -BRIDGE_Z_START)))
        front_solid, front_glass = tube_faces(axis, front=True)
        anchor = (0, 12, -BRIDGE_Z_START) if axis == "x" else (12, 0, -BRIDGE_Z_START)
        out.append(finish(front_solid, zoom, anchor, overlays=[(front_glass, 0.45)]))
        # Pillar: one height level of a slim column; the game stacks it from the ground up to the bridge.
        p = Scene()
        if axis == "x":
            p.box(7.1, 0, 0, 8.9, 1.6, LEVEL, WHITE)
            p.box(8.9, 0.6, 2, 9.0, 1.0, 6, CYAN)
        else:
            p.box(0, 7.1, 0, 1.6, 8.9, LEVEL, WHITE)
            p.box(0.6, 8.9, 2, 1.0, 9.0, 6, CYAN)
        out.append(finish(p, zoom, (0, 0, 0)))
    # Heads in the game's order: four level heads on sloped ground, then four ramps on flat ground, each by the
    # direction the bridge leaves the head: SW, SE, NE, NW.
    dirs = {"SW": ("x", +1), "SE": ("y", +1), "NE": ("x", -1), "NW": ("y", -1)}
    for ramp in (False, True):
        for d in ("SW", "SE", "NE", "NW"):
            axis, sign = dirs[d]
            s = Scene()
            def h(x, y, axis=axis, sign=sign):
                t = x if axis == "x" else y
                if not ramp:
                    return LEVEL
                return LEVEL * (t / T if sign > 0 else (T - t) / T)
            def W(u, t, z):
                return (t, 8 + u, z) if axis == "x" else (8 + u, t, z)
            # embankment: sloped top and side walls down to the ground
            for u in (-6, 6):
                s.quad(W(u, 0, 0), W(u, T, 0), W(u, T, h(*W(u, T, 0)[:2]) ), W(u, 0, h(*W(u, 0, 0)[:2])), CONCRETE_D)
            s.quad(W(-6, 0, h(*W(-6, 0, 0)[:2])), W(6, 0, h(*W(6, 0, 0)[:2])), W(6, T, h(*W(6, T, 0)[:2])), W(-6, T, h(*W(-6, T, 0)[:2])), CONCRETE_D)
            far = T if sign > 0 else 0
            s.quad(W(-6, far, 0), W(6, far, 0), W(6, far, h(*W(6, far, 0)[:2])), W(-6, far, h(*W(-6, far, 0)[:2])), CONCRETE_D)
            out.append(finish(s, zoom, (0, 0, 0)))
    return out


def bridge_surfaces(zoom):
    """The guideway on the deck: X, Y, then sloped for heads leaving NE, SE, SW, NW."""
    out = []
    for piece in (X_PIECE, Y_PIECE):
        s = Scene()
        guideway(s, *piece, bed=False)
        out.append(finish(s, zoom, (0, 0, 0)))
    rising = {"NE": SLOPES["NE"], "SE": SLOPES["SE"], "SW": SLOPES["SW"], "NW": SLOPES["NW"]}
    for d in ("NE", "SE", "SW", "NW"):
        # A head leaving towards d rises towards d: the bridge is that way.
        piece, z_at = rising[d]
        s = Scene()
        guideway(s, *piece, z_at=z_at, bed=False)
        out.append(finish(s, zoom, (0, 0, 0)))
    return out


# --- tube portals ----------------------------------------------------------------------------------------------
def portal_sprites(zoom):
    """Ground (concrete pad and guideway) and hood for tubes going NE, SE, SW, NW from the portal."""
    ground, hood = [], []
    for d in ("NE", "SE", "SW", "NW"):
        axis = "x" if d in ("NE", "SW") else "y"
        into = -1 if d in ("NE", "NW") else +1  # direction along the axis into the tube
        g = Scene()
        g.quad((0, 0, 0), (T, 0, 0), (T, T, 0), (0, T, 0), CONCRETE_D)
        guideway(g, *(X_PIECE if axis == "x" else Y_PIECE), bed=False)
        ground.append(finish(g, zoom, (0, 0, 0)))
        s = Scene()
        arch = [(-6, 0), (-6, 6), (-4.5, 9), (-1.5, 10.5), (1.5, 10.5), (4.5, 9), (6, 6), (6, 0)]
        mouth_t = 4 if into > 0 else 12  # the mouth faces away from the tube
        tail_t = 15.5 if into > 0 else 0.5
        def W(u, t, z):
            return (t, 8 + u, z) if axis == "x" else (8 + u, t, z)
        for i in range(len(arch) - 1):
            (u0, z0), (u1, z1) = arch[i], arch[i + 1]
            m = PANEL if (u0 + u1) / 2 < 0 else WHITE
            s.quad(W(u0, mouth_t, z0), W(u1, mouth_t, z1), W(u1 * 0.9, tail_t, 0.6), W(u0 * 0.9, tail_t, 0.6), m)
        mouth = [(-4.2, 0.5), (-4.2, 5), (-3, 7), (-1, 7.8), (1, 7.8), (3, 7), (4.2, 5), (4.2, 0.5)]
        mt = mouth_t - 0.05 * into
        for i in range(1, len(mouth) - 1):
            s.tri(W(mouth[0][0], mt, mouth[0][1]), W(mouth[i][0], mt, mouth[i][1]), W(mouth[i + 1][0], mt, mouth[i + 1][1]), DARK)
        def band(t0, t1, z0, z1, m):
            if axis == "x":
                s.box(min(t0, t1), 8 - 6.1, z0, max(t0, t1), 8 + 6.1, z1, m)
            else:
                s.box(8 - 6.1, min(t0, t1), z0, 8 + 6.1, max(t0, t1), z1, m)
        band(mouth_t - 0.3 * into, mouth_t + 0.6 * into, 6.2, 7.2, CC)
        band(mouth_t - 0.35 * into, mouth_t + 0.3 * into, 7.6, 8.1, CYAN)
        # The game anchors portal hoods at the tile point (15, 15, 0).
        hood.append(finish(s, zoom, (15, 15, 0)))
    return ground, hood


# --- depot -----------------------------------------------------------------------------------------------------
def depot_scene(facing):
    sys.path.insert(0, str(HERE))
    from depot_model import depot
    s = Scene()
    depot(s, 0, 0, facing)
    return s


def depot_sprites(zoom):
    """SE_1, SE_2, SW_1, SW_2, NE, NW, anchored at the bounding-box origins of the base game's depot layout."""
    out = []
    # The whole shed is the front sprite, so trains go into it rather than through a seam across its roof; the back
    # sprite of a two-part depot is left empty.
    out.append(empty())
    out.append(finish(depot_scene("+y"), zoom, (13, 2, 0)))  # SE: door facing +y
    out.append(empty())
    out.append(finish(depot_scene("+x"), zoom, (2, 13, 0)))  # SW: door facing +x
    out.append(finish(depot_scene("-x"), zoom, (2, 13, 0)))  # NE
    out.append(finish(depot_scene("-y"), zoom, (13, 2, 0)))  # NW
    return out


# --- terminal --------------------------------------------------------------------------------------------------
ARCH = [(-8, 4), (-8, 11), (-7, 14), (-5, 16.2), (-2, 17.4), (2, 17.4), (5, 16.2), (7, 14), (8, 11), (8, 4)]


def terminal_scenes(axis):
    """Back and front halves of one terminal tile along axis, and the translucent roof glass."""
    s = Scene()
    def B(u0, u1, t0, t1, z0, z1, m):
        if axis == "x":
            s.box(t0, 8 + u0, z0, t1, 8 + u1, z1, m)
        else:
            s.box(8 + u0, t0, z0, 8 + u1, t1, z1, m)
    def W(u, t, z):
        return (t, 8 + u, z) if axis == "x" else (8 + u, t, z)
    for side in (-1, 1):
        lo, hi = (-8, -4.6) if side < 0 else (4.6, 8)
        B(lo, hi, 0, T, 0, 4, PLATFORM)
        e = hi - 0.5 if side < 0 else lo
        B(e, e + 0.5, 0, T, 4, 4.12, EDGE)
        g = hi - 0.3 if side < 0 else lo
        B(g, g + 0.3, 0, T, 3.4, 4.0, CYAN)
        B(lo, hi, 0, T, 4, 4.05, PLATFORM) if False else None
    # ribs at both tile edges and the middle, with the company-colour fascia along both eaves
    for t in (0.45, 8, 15.55):
        for i in range(len(ARCH) - 1):
            (u0, z0), (u1, z1) = ARCH[i], ARCH[i + 1]
            s.quad(W(u0, t - 0.45, z0), W(u1, t - 0.45, z1), W(u1, t + 0.45, z1), W(u0, t + 0.45, z0), WHITE)
    for side in (-1, 1):
        B(side * 8 - 0.6, side * 8 + 0.6, 0, T, 10, 11.5, CC)
        for t in (0.45, 8, 15.55):
            B(side * 7.6 - 0.4, side * 7.6 + 0.4, t - 0.4, t + 0.4, 4, 10, WHITE)
    glass = Scene()
    for i in range(1, len(ARCH) - 2):
        (u0, z0), (u1, z1) = ARCH[i], ARCH[i + 1]
        glass.quad(W(u0, 0, z0), W(u1, 0, z1), W(u1, T, z1), W(u0, T, z0), CANOPY_GLASS)
    u_of = (lambda x, y, z: y - 8) if axis == "x" else (lambda x, y, z: x - 8)
    back = s.subset(lambda x, y, z: u_of(x, y, z) < 0 and z < 10.5)
    front = s.subset(lambda x, y, z: not (u_of(x, y, z) < 0 and z < 10.5))
    return back, front, glass


def terminal_sprites(zoom):
    """For X then Y: back (anchored at the tile corner) and front (anchored at the front platform's box)."""
    out = []
    for axis in ("x", "y"):
        back, front, glass = terminal_scenes(axis)
        out.append(finish(back, zoom, (0, 0, 0)))
        anchor = (0, 11, 0) if axis == "x" else (11, 0, 0)
        out.append(finish(front, zoom, anchor, overlays=[(glass, 0.34)]))
    return out


# --- pods ------------------------------------------------------------------------------------------------------
def pod(s, heading_deg, kind, cz):
    """kind: 'pod' (nose forward), 'pass' (window band) or 'mail' (no windows)."""
    a = math.radians(heading_deg)
    ca, sa = math.cos(a), math.sin(a)
    def P(u, v, z):
        return (u * ca - v * sa, u * sa + v * ca, cz + z)
    N = 14
    Wd, Hh, base = 2.6, 2.9, 3.0
    prof = [(Wd * math.cos(2 * math.pi * i / N), max(0.35, base + Hh * math.sin(2 * math.pi * i / N) * 1.05)) for i in range(N)]
    half = 4.6
    if kind == "pod":
        rings = [(-half, 0.55), (-half + 0.8, 0.85), (-half + 1.6, 1.0), (half - 3.0, 1.0), (half - 1.9, 0.86), (half - 1.0, 0.62), (half - 0.35, 0.32), (half, 0.06)]
    else:
        rings = [(-half, 0.6), (-half + 0.8, 0.9), (-half + 1.6, 1.0), (half - 1.6, 1.0), (half - 0.8, 0.9), (half, 0.6)]
    for k in range(len(rings) - 1):
        (v0, s0), (v1, s1) = rings[k], rings[k + 1]
        for i in range(N):
            (u0, z0), (u1, z1) = prof[i], prof[(i + 1) % N]
            zm, um = (z0 + z1) / 2, (u0 + u1) / 2
            m = WHITE
            if 2.6 <= zm <= 4.2:
                m = CC
            elif zm < 1.0:
                m = PANEL
            elif 4.5 <= zm <= 5.4 and abs(um) > 0.9 and kind == "pass" and 0 < k < len(rings) - 2:
                m = WIN
            if kind == "pod" and k >= len(rings) - 4 and 3.4 <= zm <= 5.6:
                m = WIN  # wrap-around windscreen
            f = lambda u, z, sc: (u * sc, base + (z - base) * sc)  # noqa: E731
            a0, a1 = f(u0, z0, s0), f(u1, z1, s0)
            b0, b1 = f(u0, z0, s1), f(u1, z1, s1)
            s.quad(P(a0[0], v0, a0[1]), P(b0[0], v1, b0[1]), P(b1[0], v1, b1[1]), P(a1[0], v0, a1[1]), m)
        if kind == "mail" and k == 2:
            pass
    for side in (-1, 1):
        s.quad(P(side * 2.2, -half + 1, 0.12), P(side * 2.2, half - 1, 0.12), P(side * 2.2, half - 1, 0.45), P(side * 2.2, -half + 1, 0.45), CYAN)
    if kind == "mail":  # a white mail stripe across the company band
        for side in (-1, 1):
            s.quad(P(side * 2.62, -0.9, 2.8), P(side * 2.62, 0.9, 2.8), P(side * 2.62, 0.9, 4.0), P(side * 2.62, -0.9, 4.0), WHITE)


DIRECTIONS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
HEADING = {d: (135 - 45 * i) % 360 for i, d in enumerate(DIRECTIONS)}
POD_Z = 3.3  # pods hover just above the guideway's magnetic rails


def vehicle_sprites(zoom, kind):
    out = []
    for d in DIRECTIONS:
        s = Scene()
        pod(s, HEADING[d], kind, POD_Z)
        out.append(finish(s, zoom, (0, 0, 0)))
    return out


# --- toolbar icons and cursors ---------------------------------------------------------------------------------
def gui_sprites():
    """Eight toolbar icons then eight cursors, at normal zoom only (the GUI scales them)."""
    def icon(build):
        s = Scene()
        build(s)
        img, mask, (ox, oy) = s.render(zoom=1)
        img = img.crop(img.getbbox())
        mask = mask.crop((0, 0, img.width, img.height))
        canvas = Image.new("RGBA", (20, 20))
        k = min(1.0, 18 / max(img.width, img.height))
        if k < 1:
            img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.NEAREST)
        canvas.alpha_composite(img, ((20 - img.width) // 2, (20 - img.height) // 2))
        return canvas, Image.new("L", canvas.size), 0, 0
    def piece(p):
        return lambda s: guideway(s, *p)
    def depot_icon(s):
        from depot_model import depot
        depot(s, 0, 0, "+y")
    def tube_icon(s):
        hood = portal_scene_for_icon()
        s.tris += hood.tris
    def convert_icon(s):
        guideway(s, *X_PIECE)
        s.box(6, 6, 5, 10, 10, 7, CYAN)
    def auto_icon(s):
        guideway(s, *X_PIECE)
        guideway(s, *Y_PIECE, bed=False)
    builders = [piece(N_PIECE), piece(X_PIECE), piece(E_PIECE), piece(Y_PIECE), auto_icon, depot_icon, tube_icon, convert_icon]
    icons = [icon(b) for b in builders]
    cursors = []
    for img, mask, _, _ in icons:
        c = Image.new("RGBA", (32, 32))
        c.alpha_composite(img, (6, 6))
        # a small white arrow at the hotspot, top left
        a = np.asarray(c).copy()
        for i in range(7):
            a[i, 0:7 - i] = (255, 255, 255, 255)
            a[i, 7 - i] = (0, 0, 0, 255)
        cursors.append((Image.fromarray(a), Image.new("L", c.size), 0, 0))
    return icons + cursors


def portal_scene_for_icon():
    s = Scene()
    arch = [(-6, 0), (-6, 6), (-4.5, 9), (-1.5, 10.5), (1.5, 10.5), (4.5, 9), (6, 6), (6, 0)]
    for i in range(len(arch) - 1):
        (u0, z0), (u1, z1) = arch[i], arch[i + 1]
        s.quad((12, 8 + u0, z0), (12, 8 + u1, z1), (2, 8 + u1 * 0.9, 0.6), (2, 8 + u0 * 0.9, 0.6), WHITE)
    mouth = [(-4.2, 0.5), (-4.2, 5), (-3, 7), (-1, 7.8), (1, 7.8), (3, 7), (4.2, 5), (4.2, 0.5)]
    for i in range(1, len(mouth) - 1):
        s.tri((12.05, 8 + mouth[0][0], mouth[0][1]), (12.05, 8 + mouth[i][0], mouth[i][1]), (12.05, 8 + mouth[i + 1][0], mouth[i + 1][1]), DARK)
    return s


# --- output ----------------------------------------------------------------------------------------------------
DOS = bytes(raw_palette_data[0])
CC_BASE = 198  # first company-colour palette index; 202 is its middle shade


def save(name, sprites, zoom):
    """Save a strip of sprites (and its company-colour mask if any) and return NML sprite entries."""
    w = sum(img.width + 1 for img, _, _, _ in sprites)
    h = max(img.height for img, _, _, _ in sprites)
    strip = Image.new("RGBA", (w, h))
    mstrip = Image.new("P", (w, h))
    mstrip.putpalette(DOS)
    has_mask = False
    entries = []
    x = 0
    for img, mask, xrel, yrel in sprites:
        a = np.asarray(img).copy()
        m = np.asarray(mask) > 0
        if m.any():
            has_mask = True
            # Masked pixels: grey with their shade as brightness; the mask names the company colour to use.
            lum = a[..., :3].astype(float).max(-1)
            g = np.clip(lum, 1, 255).astype(np.uint8)
            a[m, 0] = g[m]
            a[m, 1] = g[m]
            a[m, 2] = g[m]
            mi = np.zeros(m.shape, np.uint8)
            mi[m] = CC_BASE + 4
            mimg = Image.fromarray(mi, "P")
            mimg.putpalette(DOS)
            mstrip.paste(mimg, (x, 0))
        strip.alpha_composite(Image.fromarray(a), (x, 0))
        entries.append(f"[{x}, 0, {img.width}, {img.height}, {xrel}, {yrel}]")
        x += img.width + 1
    path = GFX / f"{name}_{zoom}x.png"
    strip.save(path)
    mask_path = None
    if has_mask:
        mask_path = GFX / f"{name}_{zoom}x_mask.png"
        mstrip.save(mask_path)
    return entries, path.name, (mask_path.name if mask_path else None)


def spriteset(name, generator):
    lines = []
    for zoom in (1, 2):
        entries, file, mask = save(name, generator(zoom), zoom)
        head = "spriteset" if zoom == 1 else "alternative_sprites"
        level = "ZOOM_LEVEL_NORMAL" if zoom == 1 else "ZOOM_LEVEL_IN_2X"
        mask_arg = f', "gfx/hyperloop/{mask}"' if mask else ""
        lines.append(f'{head}(hyperloop_{name}_sprites, {level}, BIT_DEPTH_32BPP, "gfx/hyperloop/{file}"{mask_arg}) {{')
        lines += [f"    {e}" for e in entries]
        lines.append("}")
    return lines


def main():
    GFX.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(HERE))
    portal_cache = {}
    def portal(zoom, which):
        if zoom not in portal_cache:
            portal_cache[zoom] = portal_sprites(zoom)
        return portal_cache[zoom][which]
    sets = [
        ("track_underlay", lambda z: track_sprites(z, overlay=False)),
        ("track_overlay", lambda z: track_sprites(z, overlay=True)),
        ("bridge", lambda z: bridge_surfaces(z) + viaduct_structure(z)),
        ("tunnel_ground", lambda z: portal(z, 0)),
        ("tunnel_portal", lambda z: portal(z, 1)),
        ("depots", depot_sprites),
        ("fences", lambda z: [empty() for _ in range(16)]),
        ("terminal", terminal_sprites),
        ("pod", lambda z: vehicle_sprites(z, "pod")),
        ("passenger_capsule", lambda z: vehicle_sprites(z, "pass")),
        ("mail_capsule", lambda z: vehicle_sprites(z, "mail")),
    ]
    lines = ["/* BEGIN generated Hyperloop sprites (tools/hyperloop/make_hyperloop_art.py) */"]
    for name, gen in sets:
        lines += spriteset(name, gen)
    # GUI: normal zoom only.
    entries, file, _ = save("gui", gui_sprites(), 1)
    lines.append(f'spriteset(hyperloop_gui_sprites, ZOOM_LEVEL_NORMAL, BIT_DEPTH_32BPP, "gfx/hyperloop/{file}") {{')
    lines += [f"    {e}" for e in entries]
    lines.append("}")
    lines.append("/* END generated Hyperloop sprites */")
    nml = FL / "future_logistics.nml"
    text = nml.read_text()
    a = text.index(lines[0])
    b = text.index(lines[-1]) + len(lines[-1])
    nml.write_text(text[:a] + "\n".join(lines) + text[b:])
    print("wrote", sum(1 for l in lines if l.strip().startswith("[")), "sprite entries")


if __name__ == "__main__":
    main()
