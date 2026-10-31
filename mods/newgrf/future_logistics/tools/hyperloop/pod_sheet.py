import sys, math
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3] / 'tools'))
from isorender import Scene, Material, recolour
from PIL import Image, ImageDraw, ImageFont
import numpy as np

WHITE = Material((246, 248, 250)); PANEL = Material((200, 208, 216)); DARK = Material((30, 34, 44))
WIN = Material((20, 26, 40)); CC = Material((40, 90, 200), company=True); CYAN = Material((90, 240, 255), glow=True)
GLOWR = Material((255, 70, 60), glow=True)

def pod(scene, heading_deg, length=13, cx=0, cy=0, cz=0):
    """A rounded pod pointing along heading, built from scaled profile rings so the nose tapers smoothly."""
    a = math.radians(heading_deg)
    ca, sa = math.cos(a), math.sin(a)
    def P(u, v, z):
        return (cx + u*ca - v*sa, cy + u*sa + v*ca, cz + z)
    N = 14
    W, Hh, base = 2.6, 2.9, 3.0   # half-width, half-height, centre height
    prof = [(W*math.cos(2*math.pi*i/N), base + Hh*math.sin(2*math.pi*i/N)*1.05) for i in range(N)]
    prof = [(u, max(0.35, z)) for u, z in prof]
    def mat(z_mid, u_mid):
        if 4.5 <= z_mid <= 5.4 and abs(u_mid) > 0.9: return WIN
        if 2.6 <= z_mid <= 4.2: return CC
        if z_mid < 1.0: return PANEL
        return WHITE
    half = length/2; body = half - 3.6
    rings = [(-half, 0.08), (-half+0.7, 0.45), (-half+1.6, 0.72), (-half+2.6, 0.9), (-body, 1.0), (body, 1.0), (half-2.6, 0.9), (half-1.6, 0.72), (half-0.7, 0.45), (half, 0.08)]
    for k in range(len(rings)-1):
        (v0, s0), (v1, s1) = rings[k], rings[k+1]
        for i in range(N):
            (u0, z0), (u1, z1) = prof[i], prof[(i+1) % N]
            zm, um = (z0+z1)/2, (u0+u1)/2
            m = mat(zm, um)
            nose = k in (0, len(rings)-2)
            if nose and m is WIN: m = WHITE
            if (k in (1, len(rings)-3)) and 3.6 <= zm <= 5.3: m = WIN   # wrap-around windscreen
            f = lambda u, z, sc: (u*sc, base + (z-base)*sc)
            a0, a1 = f(u0, z0, s0), f(u1, z1, s0)
            b0, b1 = f(u0, z0, s1), f(u1, z1, s1)
            scene.quad(P(a0[0], v0, a0[1]), P(b0[0], v1, b0[1]), P(b1[0], v1, b1[1]), P(a1[0], v0, a1[1]), m)
    # cyan underglow skids
    for side in (-1, 1):
        scene.quad(P(side*2.2, -body, 0.12), P(side*2.2, body, 0.12), P(side*2.2, body, 0.45), P(side*2.2, -body, 0.45), CYAN)

fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
cells = []
for heading in (0, 45, 90, 135):
    s = Scene(); pod(s, heading)
    img, mask, _ = s.render(zoom=2)
    cells.append((f"{heading}°", img, mask))
row = []
for name, img, mask in cells:
    row.append(img)
cols = [("blue", (40, 90, 200)), ("red", (200, 40, 40)), ("green", (40, 160, 60)), ("orange", (230, 130, 20))]
recs = [recolour(cells[1][1], cells[1][2], rgb) for _, rgb in cols]
grass = (70, 128, 45, 255)
def tile(im, k=3):
    bg = Image.new("RGBA", (im.width + 16, im.height + 16), grass); bg.alpha_composite(im, (8, 8))
    return bg.resize((bg.width * k, bg.height * k), Image.NEAREST)
r1 = [tile(i) for i in row]; r2 = [tile(i) for i in recs]
maglev = Image.open("maglev_reference.png").convert("RGBA").crop((95, 360, 175, 405))
maglev = maglev.resize((maglev.width * 3, maglev.height * 3), Image.NEAREST)
W = max(sum(i.width for i in r1), sum(i.width for i in r2) + maglev.width + 40) + 20 * 6
H = max(i.height for i in r1) + max(i.height for i in r2) + 120
sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255)); d = ImageDraw.Draw(sheet)
d.text((20, 8), "Pod in four directions (2x zoom, enlarged 3x); the game uses eight", fill=(0, 0, 0, 255), font=fb)
x = 20
for i in r1: sheet.alpha_composite(i, (x, 32)); x += i.width + 20
y = 40 + max(i.height for i in r1) + 10
d.text((20, y), "Company colours: blue, red, green, orange", fill=(0, 0, 0, 255), font=fb)
x = 20
for i in r2: sheet.alpha_composite(i, (x, y + 24)); x += i.width + 20
d.text((x + 10, y), "Base-game maglev, same zoom", fill=(0, 0, 0, 255), font=fb)
sheet.alpha_composite(maglev, (x + 10, y + 24))
sheet.convert("RGB").save("pod_sheet.png"); print(sheet.size)
