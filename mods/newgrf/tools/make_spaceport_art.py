#!/usr/bin/env python3
# GPL-2.0-only. Makes the chunky spaceport and Starship art from the handoff images. Needs Pillow, NumPy, SciPy.
#
#   python3 mods/newgrf/tools/make_spaceport_art.py [output-folder]
#
# Sources (all 1254 px, drawn for a 3x4-tile footprint):
#   corporate_infrastructure/originals/spaceport_empty_pad_transparent.png    the pad with the tower arms swung open
#   corporate_infrastructure/originals/spaceport_starship_on_pad_transparent.png  the same pad with Starship docked
#   starship/art/starship_powered.png                                          Starship in flight, engines lit
# Outputs, per zoom level (1 = normal, 2 = 2x zoom), in one pixel density with the base game:
#   pad_empty_{z}x.png, pad_docked_{z}x.png    the whole pad, before slicing into tiles
#   rocket_idle_{z}x.png                       Starship cut from the docked pad, arms removed
#   rocket_lit_{z}x_{f}.png                    Starship with flame, three flicker frames
#   layout.json                                where the footprint and the launch mount are in each image
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pixelart as P  # noqa: E402

NEWGRF = Path(__file__).resolve().parent.parent
ORIGINALS = NEWGRF / "corporate_infrastructure" / "originals"
POWERED = NEWGRF / "starship" / "art" / "starship_powered.png"

# The pad's ground diamond in the source images, measured: west, east and south corners.
WEST, EAST, SOUTH = (103, 846), (1152, 896), (705, 1141)
FOOTPRINT = (3, 4)  # tiles along x (down-left) and y (down-right)
CROP = (103, 0, 1153, 1142)  # the full width of the ground diamond, so the art grid lines up with the tiles
# Starship in the docked image: its column, and the two bands where the tower's clamp arms cross in front of it.
ROCKET_BOX = (640, 205, 753, 866)
ROCKET_BODY = (658, 736)
ARM_BANDS = [(280, 354), (478, 510)]
# The powered image's booster is this much wider than the docked one (100 px against 78 px, measured).
POWERED_SCALE = 78 / 100
FLAME_START = 848  # First row of flame below the engines in the powered image (measured).


def source_per_pixel(zoom):
    """Source pixels per game pixel: the ground diamond spans (tiles_x + tiles_y) * 32 game pixels at normal zoom."""
    return (CROP[2] - CROP[0]) / ((FOOTPRINT[0] + FOOTPRINT[1]) * P.TILE_W // 2 * zoom)


def to_grid(image, zoom, colours):
    """Snap a cropped source image to game pixels at this zoom level."""
    f = source_per_pixel(zoom)
    return P.pixelate(image, max(1, round(image.width / f)), colours, grid_h=max(1, round(image.height / f)))


def cut_rocket(docked, empty):
    """Starship's pixels from the docked image, with the clamp arms in front of it painted out from the hull."""
    x0, y0, x1, y1 = ROCKET_BOX
    s = np.asarray(docked).astype(int)
    e = np.asarray(empty).astype(int)
    col = s[y0:y1, x0:x1].copy()
    inbody = np.zeros(x1 - x0, bool)
    inbody[ROCKET_BODY[0] - x0:ROCKET_BODY[1] - x0] = True
    keep = (col[..., 3] > 128) & ((e[y0:y1, x0:x1, 3] < 64) | inbody[None, :])
    lab, n = ndimage.label(keep)
    keep = lab == 1 + int(np.argmax(ndimage.sum(keep, lab, range(1, n + 1))))
    col[~keep] = 0
    for a, b in ARM_BANDS:
        above, below = col[a - y0 - 1].copy(), col[b - y0 + 1].copy()
        for k in range(b - a + 1):
            col[a - y0 + k] = above if k < (b - a) / 2 else below
    image = Image.fromarray(col.astype(np.uint8), "RGBA")
    box = image.getbbox()
    return image.crop(box), (x0 + box[0], y0 + box[1])


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else NEWGRF / "starship" / "gfx"
    out.mkdir(parents=True, exist_ok=True)
    empty = Image.open(ORIGINALS / "spaceport_empty_pad_transparent.png").convert("RGBA")
    docked = Image.open(ORIGINALS / "spaceport_starship_on_pad_transparent.png").convert("RGBA")
    powered = Image.open(POWERED).convert("RGBA")
    box = P.solid_bbox(powered, 40)
    powered = powered.crop(box)
    flame_start = (FLAME_START - box[1]) * POWERED_SCALE
    powered = powered.resize((round(powered.width * POWERED_SCALE), round(powered.height * POWERED_SCALE)), Image.BOX)
    rocket, rocket_at = cut_rocket(docked, empty)
    north = (WEST[0] + EAST[0] - SOUTH[0], WEST[1] + EAST[1] - SOUTH[1])
    layout = {"footprint": FOOTPRINT}
    for zoom in (1, 2):
        f = source_per_pixel(zoom)
        for name, image in (("pad_empty", empty), ("pad_docked", docked)):
            to_grid(image.crop(CROP), zoom, 96).save(out / f"{name}_{zoom}x.png")
        idle = to_grid(rocket, zoom, 48)
        idle.save(out / f"rocket_idle_{zoom}x.png")
        lit = to_grid(powered, zoom, 48)
        # Flicker: the flame below the engines is stretched slightly differently in each frame.
        body_h = round(flame_start / f)
        for frame, stretch in enumerate((1.0, 1.12, 0.9)):
            flame = lit.crop((0, body_h, lit.width, lit.height))
            flame = flame.resize((flame.width, max(1, round(flame.height * stretch))), Image.NEAREST)
            img = Image.new("RGBA", (lit.width, body_h + flame.height))
            img.alpha_composite(lit.crop((0, 0, lit.width, body_h)))
            img.alpha_composite(flame, (0, body_h))
            img.save(out / f"rocket_lit_{zoom}x_{frame}.png")
        layout[f"{zoom}x"] = {
            # The footprint's north corner in the pad images, and the docked rocket's top-left corner, in game pixels.
            "north": [round((north[0] - CROP[0]) / f), round((north[1] - CROP[1]) / f)],
            "rocket_at": [round((rocket_at[0] - CROP[0]) / f), round((rocket_at[1] - CROP[1]) / f)],
            "rocket_size": list(idle.size),
        }
    (out / "spaceport_layout.json").write_text(json.dumps(layout, indent=1) + "\n")
    print(json.dumps(layout))


if __name__ == "__main__":
    main()
