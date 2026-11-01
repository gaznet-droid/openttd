"""Style check: Hyperloop pieces at normal zoom on real game grass, next to the base-game maglev station."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from isorender import Scene
from depot_model import depot, guideway, T
import concept_scene as cs
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
OUT = Path(sys.argv[1])
whole = Image.open(sys.argv[2]).convert("RGBA")
W, H = whole.size
def px(tx, ty): return (ty - tx) * 32 + 255 * 32 + 32, (tx + ty) * 16 + (H - 510 * 16)

def on_grass(img, origin, tile0, margin=24):
    nx, ny = px(*tile0)
    at = (int(nx) + origin[0], int(ny) + origin[1])
    base = whole.crop((at[0] - margin, at[1] - margin, at[0] + img.width + margin, at[1] + img.height + margin))
    base.alpha_composite(img, (margin, margin))
    return base

# 1. the concept scene with a depot at the far end of the terminal, door facing the terminal
depot(cs.s, 1, -1, "+y")
img, origin = cs.render_with_glass(cs.s, 1)
scene = on_grass(img, origin, (20, 40))
# 2. the depot in its four orientations, each with its guideway stub
row = []
for facing in ("+x", "+y", "-x", "-y"):
    d = Scene(); depot(d, 0, 0, facing)
    im, _, o = d.render(zoom=1)
    row.append((facing, on_grass(im, o, (20, 40), margin=22)))
maglev = Image.open(sys.argv[3]).convert("RGBA")
fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
K = 3
names = {"+x": "door: down-left", "+y": "door: down-right", "-x": "door: up-right", "-y": "door: up-left"}
rw = sum(i.width for _, i in row) + 12 * (len(row) + 1)
Wd = max(scene.width + maglev.width + 36, rw)
Hd = max(scene.height, maglev.height) + max(i.height for _, i in row) + 70
sheet = Image.new("RGBA", (Wd, Hd), (255, 255, 255, 255)); d = ImageDraw.Draw(sheet)
d.text((12, 4), "New Hyperloop pieces, normal zoom", fill=(0, 0, 0, 255), font=fb)
sheet.alpha_composite(scene, (12, 20))
d.text((scene.width + 24, 4), "Base-game maglev station", fill=(0, 0, 0, 255), font=fb)
sheet.alpha_composite(maglev, (scene.width + 24, 20))
y = 26 + max(scene.height, maglev.height)
d.text((12, y), "Depot in its four orientations; the guideway enters through the door", fill=(0, 0, 0, 255), font=fb)
x = 12
for facing, im in row:
    sheet.alpha_composite(im, (x, y + 30)); d.text((x, y + 16), names[facing], fill=(70, 70, 70, 255), font=f); x += im.width + 12
sheet = sheet.convert("RGB")
sheet.resize((sheet.width * K, sheet.height * K), Image.NEAREST).save(OUT)
print(sheet.size)
