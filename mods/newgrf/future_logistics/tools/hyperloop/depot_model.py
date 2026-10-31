"""The Hyperloop pod depot: a one-tile service hangar the guideway runs into."""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from isorender import Material  # noqa: E402

T = 16
WHITE = Material((214, 218, 222))
PANEL = Material((178, 186, 194))
ROOF = Material((200, 206, 212))
DARK = Material((26, 30, 40), grain=0.02)
GLASS = Material((90, 150, 175))
CONCRETE = Material((176, 178, 176), grain=0.12)
CONCRETE_D = Material((138, 140, 140), grain=0.12)
CYAN = Material((90, 240, 255), glow=True)
CC = Material((40, 90, 200), company=True)


def guideway(s, axis, a0, a1, c, z=0):
    """Guideway beam along axis between a0 and a1, centred on c across it."""
    def B(u0, u1, v0, v1, z0, z1, m):
        if axis == "y":
            s.box(c + u0, a0 + v0, z0, c + u1, a1 + v1, z1, m)
        else:
            s.box(a0 + v0, c + u0, z0, a1 + v1, c + u1, z1, m)
    B(-6, 6, 0, 0, z, z + 1, CONCRETE_D)
    B(-4, 4, 0, 0, z + 1, z + 3, CONCRETE)
    B(-3.2, -2.2, 0, 0, z + 3, z + 3.4, CYAN)
    B(2.2, 3.2, 0, 0, z + 3, z + 3.4, CYAN)
    B(-1, 1, 0, 0, z + 3, z + 3.2, DARK)


def depot(s, tx, ty, facing):
    """A depot on tile (tx, ty) whose door faces 'facing': one of '+x', '+y', '-x', '-y'.

    Built along the axis the door faces; the guideway stub runs out through the door to the tile edge."""
    x0, y0 = tx * T, ty * T
    axis = "x" if facing in ("+x", "-x") else "y"
    sign = 1 if facing[0] == "+" else -1
    c = (y0 if axis == "x" else x0) + T / 2   # centre across the axis
    lo, hi = (x0, x0 + T) if axis == "x" else (y0, y0 + T)
    back = lo + 2 if sign > 0 else hi - 2       # rear wall position along the axis
    front = hi - 2.5 if sign > 0 else lo + 2.5  # door wall position
    a, b = min(back, front), max(back, front)

    def box(u0, u1, v0, v1, z0, z1, m, top=None):
        if axis == "x":
            s.box(v0, c + u0, z0, v1, c + u1, z1, m, top=top)
        else:
            s.box(c + u0, v0, z0, c + u1, v1, z1, m, top=top)

    def quad_uvz(p, m):
        pts = [((v, c + u, z) if axis == "x" else (c + u, v, z)) for (u, v, z) in p]
        s.quad(*pts, m)

    # plinth and walls
    box(-7.5, 7.5, a - 0.5, b + 0.5, 0, 1, CONCRETE_D)
    box(-7, 7, a, b, 1, 9, WHITE)
    # glazed clerestory band and company-colour band along both long sides
    box(-7.1, 7.1, a + 1, b - 1, 6.4, 7.8, GLASS)
    box(-7.15, 7.15, a, b, 4.2, 5.6, CC)
    # curved roof
    arch = [(-7.6, 9), (-6.5, 11), (-4.5, 12.6), (-1.6, 13.4), (1.6, 13.4), (4.5, 12.6), (6.5, 11), (7.6, 9)]
    for i in range(len(arch) - 1):
        (u0, z0), (u1, z1) = arch[i], arch[i + 1]
        quad_uvz([(u0, a - 0.6, z0), (u1, a - 0.6, z1), (u1, b + 0.6, z1), (u0, b + 0.6, z0)], ROOF)
    for v in (a - 0.6, b + 0.6):  # gable ends
        for i in range(1, len(arch) - 1):
            pts = [arch[0], arch[i], arch[i + 1]]
            quad_uvz([(pts[0][0], v, pts[0][1]), (pts[1][0], v, pts[1][1]), (pts[2][0], v, pts[2][1]), (pts[2][0], v, pts[2][1])], WHITE)
    # doorway: dark opening with cyan frame, on the door wall
    dv = front + 0.05 * sign
    quad_uvz([(-4.5, dv, 1), (4.5, dv, 1), (4.5, dv, 7.5), (-4.5, dv, 7.5)], DARK)
    for u in (-4.9, 4.5):
        box(u, u + 0.4, dv - 0.3, dv + 0.3, 1, 7.9, CYAN)
    box(-4.9, 4.9, dv - 0.3, dv + 0.3, 7.5, 7.9, CYAN)
    # guideway stub from the door to the tile edge
    edge = hi if sign > 0 else lo
    guideway(s, axis, min(front, edge), max(front, edge), c)
