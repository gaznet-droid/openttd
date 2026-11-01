#!/usr/bin/env python3
# GPL-2.0-only. Turns the Drone Port's blue livery into the owning company's colour. Needs NumPy, Pillow and NML.
#
#   python3 mods/newgrf/future_logistics/tools/drone_port_company_colour.py
#
# The supplied Drone Port art has its fascias and corner bands painted blue, so every company's port came out blue.
# Those pixels are turned grey, keeping their brightness, and a company-colour mask is written beside each tile
# picture; the game then paints them in the owner's colour, shaded by that brightness. Runs after
# make_functional_sprites.py; a tile that already has a mask is left alone, so running it twice changes nothing.
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from nml.palette import raw_palette_data

FL = Path(__file__).resolve().parent.parent
GFX = FL / "gfx"
DOS = bytes(raw_palette_data[0])
CC_BASE = 198  # first company-colour palette index; 202 is its middle shade


def livery(rgba):
    """The blue livery pixels: clearly blue and saturated, not the pale window glass."""
    a = rgba.astype(float) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a[..., :3].max(-1), a[..., :3].min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    return (a[..., 3] > 0.5) & (b > r + 0.12) & (b > g + 0.05) & (sat > 0.35)


def main():
    done = 0
    for path in sorted(GFX.glob("drone_port_[0-3]_[0-3]_[12]x.png")):
        mask_path = path.with_name(path.stem + "_mask.png")
        if mask_path.exists():
            continue
        a = np.asarray(Image.open(path).convert("RGBA")).copy()
        m = livery(a)
        grey = a[..., :3].max(-1)
        for c in range(3):
            a[..., c][m] = grey[m]
        Image.fromarray(a).save(path)
        mi = np.zeros(m.shape, np.uint8)
        mi[m] = CC_BASE + 4
        mask = Image.fromarray(mi, "P")
        mask.putpalette(DOS)
        mask.save(mask_path)
        done += 1
    # Point the sprites at their masks and draw them in the owner's colour.
    nml = FL / "future_logistics.nml"
    text = nml.read_text()
    text = re.sub(r'("gfx/(drone_port_[0-3]_[0-3]_[12]x)\.png")\)', r'\1, "gfx/\2_mask.png")', text)
    text = re.sub(r'(building \{ sprite: drone_port_[0-3]_[0-3]_sprite\(0\); [^}]*?zextent: \d+;)( \})',
                  r'\1 recolour_mode: RECOLOUR_REMAP; palette: PALETTE_USE_DEFAULT;\2', text)
    nml.write_text(text)
    print("masked", done, "tile pictures")


if __name__ == "__main__":
    sys.exit(main())
