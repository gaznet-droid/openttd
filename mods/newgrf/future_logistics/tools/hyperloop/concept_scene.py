import sys, math
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3] / 'tools'))
from isorender import Scene, Material, recolour
from PIL import Image, ImageDraw
import numpy as np

T = 16  # units per tile
GRASS = Material((86, 140, 52))
GRASS2 = Material((78, 130, 47))
CONCRETE = Material((196, 198, 196))
CONCRETE_D = Material((150, 152, 152))
PLATFORM = Material((220, 222, 220))
EDGE = Material((236, 196, 40))           # platform safety line
WHITE = Material((242, 244, 246))
PANEL = Material((214, 220, 226))
DARK = Material((40, 46, 56))
GLASS = Material((70, 120, 140))
CYAN = Material((80, 240, 255), glow=True)
CC = Material((40, 90, 200), company=True)  # company colour (previewed blue)
POD_WIN = Material((24, 30, 44))

s = Scene()
TERMINAL_ARCH = []
VIADUCT_GLASS = []

def ground(x0, y0, x1, y1):
    for i in range(x0, x1):
        for j in range(y0, y1):
            m = GRASS if (i + j) % 2 else GRASS2
            s.quad((i*T, j*T, 0), ((i+1)*T, j*T, 0), ((i+1)*T, (j+1)*T, 0), (i*T, (j+1)*T, 0), m)

def guideway_y(x_tile, y0, y1, z=0):
    """A guideway running along y on tile column x_tile, from y0 to y1 (units)."""
    c = x_tile*T + T/2
    s.box(c-6, y0, z, c+6, y1, z+1, CONCRETE_D)               # bed
    s.box(c-4, y0, z+1, c+4, y1, z+3, CONCRETE)               # beam
    s.box(c-3.2, y0, z+3, c-2.2, y1, z+3.4, CYAN)             # magnetic rails
    s.box(c+2.2, y0, z+3, c+3.2, y1, z+3.4, CYAN)
    s.box(c-1, y0, z+3, c+1, y1, z+3.2, DARK)                 # centre slot

from pod_model import pod as pod_model
def pod_y(x_tile, yc, z, length=13):
    pod_model(s, 0, length=length, cx=x_tile*T + T/2, cy=yc, cz=z + 3.1)

def terminal_y(x_tile, y_tile0, n):
    """A terminal along y, n tiles long, with platforms each side and a glass canopy."""
    y0, y1 = y_tile0*T, (y_tile0+n)*T
    c = x_tile*T + T/2
    guideway_y(x_tile, y0, y1)
    for side in (-1, 1):
        px0, px1 = (c-8, c-4.5) if side < 0 else (c+4.5, c+8)
        s.box(px0, y0, 0, px1, y1, 4, PLATFORM)
        e0 = px1-0.6 if side < 0 else px0
        s.box(e0, y0, 4, e0+0.6, y1, 4.15, EDGE)
    for side in (-1, 1):
        ex = c + side*4.8
        s.box(ex-0.3, y0, 4, ex+0.3, y1, 4.25, CYAN)                 # platform edge lights
    # roof ribs: white arches every half tile
    arch = [(-8, 4), (-8, 11), (-7, 14), (-5, 16.2), (-2, 17.4), (2, 17.4), (5, 16.2), (7, 14), (8, 11), (8, 4)]
    for k in range(2*n+1):
        y = y0 + k*T/2
        for i in range(len(arch)-1):
            (u0, z0), (u1, z1) = arch[i], arch[i+1]
            s.prism("y", y-0.45, y+0.45, (0, 0), [(c+u0-0.5, z0), (c+u1-0.5, z1), (c+u1+0.5, z1), (c+u0+0.5, z0)], WHITE, caps=True) if False else None
            s.quad((c+u0, y-0.45, z0), (c+u1, y-0.45, z1), (c+u1, y+0.45, z1), (c+u0, y+0.45, z0), WHITE)
            s.quad((c+u0*1.06, y-0.45, z0), (c+u1*1.06, y-0.45, z1), (c+u1*1.06, y+0.45, z1), (c+u0*1.06, y+0.45, z0), WHITE)
    # company-colour fascia along both eaves
    for side in (-1, 1):
        s.box(c+side*8-0.6, y0, 10, c+side*8+0.6, y1, 11.5, CC)
    TERMINAL_ARCH.extend(arch)
    return (c, y0, y1)

def pylon(x, y, z_top):
    s.box(x-1.3, y-1.3, 0, x+1.3, y+1.3, 1, CONCRETE_D)
    s.box(x-0.9, y-0.9, 1, x+0.9, y+0.9, z_top-2.5, WHITE)
    s.prism("y", y-0.8, y+0.8, (x, z_top-2.5), [(-0.9, 0), (0.9, 0), (3.2, 2.5), (-3.2, 2.5)], WHITE)
    s.box(x+0.9, y-0.3, 1.5, x+1.0, y+0.3, z_top-3, CYAN)

def viaduct_y(x_tile, y0, y1, deck):
    c = x_tile*T + T/2
    zc = deck + 4.2
    r = 5.0
    oct = [(r*math.cos(math.pi/8 + i*math.pi/4), r*math.sin(math.pi/8 + i*math.pi/4)) for i in range(8)]
    # back half solid white, front lower glass band; drawn as one prism here with per-face materials
    # back and lower halves solid; the visible front side (faces 0 and 7) is glass, drawn translucent later
    solid = [i for i in range(8) if i not in (0, 7)]
    sub = [oct[i] for i in range(8)]
    for i in solid:
        (u0, z0), (u1, z1) = sub[i], sub[(i+1) % 8]
        m = WHITE if i in (1, 2, 3) else PANEL
        s.quad((c+u0, y0, zc+z0), (c+u0, y1, zc+z0), (c+u1, y1, zc+z1), (c+u1, y0, zc+z1), m)
    VIADUCT_GLASS.append((c, zc, y0, y1, [oct[7], oct[0], oct[1]]))
    # cyan running lights
    s.box(c+r*0.70, y0, zc-r*0.72-0.3, c+r*0.70+0.4, y1, zc-r*0.72+0.2, CYAN)
    for y in range(int(y0)+T//2, int(y1), T):
        pylon(c, y, zc-r+1)
        # collar ring
        s.prism("y", y-0.6, y+0.6, (c, zc), [(u*1.08, z*1.08) for u, z in oct], PANEL, caps=False)

def portal_y(x_tile, y_tile):
    """Tube entrance: a white hood over the guideway, sloping smoothly into the ground towards +y."""
    c = x_tile*T + T/2
    y0 = y_tile*T
    s.box(c-7, y0, 0, c+7, y0+T, 0.8, CONCRETE_D)
    arch = [(-6, 0), (-6, 6), (-4.5, 9), (-1.5, 10.5), (1.5, 10.5), (4.5, 9), (6, 6), (6, 0)]
    yA, yB = y0+2, y0+T
    for i in range(len(arch)-1):
        (u0, z0), (u1, z1) = arch[i], arch[i+1]
        m = PANEL if u0 < 0 and u1 <= 0 else WHITE
        s.quad((c+u0, yA, z0), (c+u1, yA, z1), (c+u1*0.9, yB, 0.8), (c+u0*0.9, yB, 0.8), m)
    mouth = [(-4.2, 0.8), (-4.2, 5), (-3, 7), (-1, 7.8), (1, 7.8), (3, 7), (4.2, 5), (4.2, 0.8)]
    for i in range(1, len(mouth)-1):
        s.tri((c+mouth[0][0], yA-0.05, mouth[0][1]), (c+mouth[i][0], yA-0.05, mouth[i][1]), (c+mouth[i+1][0], yA-0.05, mouth[i+1][1]), DARK)
    s.box(c-6.1, yA-0.3, 6.2, c+6.1, yA+0.6, 7.2, CC)
    s.box(c-5.2, yA-0.35, 7.6, c+5.2, yA+0.3, 8.1, CYAN)

ground(-1, -1, 4, 13)
X = 1
terminal_y(X, 0, 3)
pod_y(X, 0.55*T, 0, length=13)
pod_y(X, 1.45*T, 0, length=13)
pod_y(X, 2.35*T, 0, length=13)
guideway_y(X, 3*T, 5*T)
# ramp up to the viaduct (simplified: a sloped guideway)
viaduct_y(X, 5*T, 9*T, deck=8)
s.box(X*T+T/2-4, 5*T-0.01, 0, X*T+T/2+4, 5*T+2, 8, CONCRETE)
pod_y(X, 7.4*T, 8 - 3.1 + 2.6, length=13)
guideway_y(X, 9*T, 10*T)
portal_y(X, 10)

img, mask, (ox, oy) = s.render(zoom=2)
img.save("hyperloop_concept_2x.png")
# translucent glass canopy over the terminal, drawn as an overlay so the pod shows through
canopy = Scene()
c = X*T + T/2
arch = TERMINAL_ARCH
for i in range(len(arch)-1):
    (u0, z0), (u1, z1) = arch[i], arch[i+1]
    if i in (0, len(arch)-2): continue
    canopy.quad((c+u0, 0, z0), (c+u1, 0, z1), (c+u1, 3*T, z1), (c+u0, 3*T, z0), Material((150, 220, 240)))
cimg, _, (cox, coy) = canopy.render(zoom=2, origin=(ox, oy), size=img.size, outline=0.9, crease=1.0)
a = np.asarray(cimg).astype(float)
a[..., 3] *= 0.30
img.alpha_composite(Image.fromarray(a.astype(np.uint8)))
img.save("hyperloop_concept_2x.png")
print(img.size)

glass = Scene()
for (c, zc, y0, y1, pts) in VIADUCT_GLASS:
    for i in range(len(pts)-1):
        (u0, z0), (u1, z1) = pts[i], pts[i+1]
        glass.quad((c+u0, y0, zc+z0), (c+u0, y1, zc+z0), (c+u1, y1, zc+z1), (c+u1, y0, zc+z1), Material((120, 200, 225)))
gimg, _, _ = glass.render(zoom=2, origin=(ox, oy), size=img.size, outline=0.85, crease=1.0)
g = np.asarray(gimg).astype(float); g[..., 3] *= 0.42
img.alpha_composite(Image.fromarray(g.astype(np.uint8)))
img.save("hyperloop_concept_2x.png")
