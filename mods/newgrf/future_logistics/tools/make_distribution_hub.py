#!/usr/bin/env python3
# GPL-2.0-only. Draws the Distribution Centre and writes it into the Future Logistics NewGRF. Needs NumPy, Pillow, NML.
#
#   python3 mods/newgrf/future_logistics/tools/make_distribution_hub.py
#
# The facility is 5x5 (tools/hub_model.py): a 4x4 warehouse object in the north corner and eight truck bays, four
# along its south-west face and four along its south-east face; the front corner tile is left free. The warehouse is
# drawn once and cut into one piece per tile, each a building sprite boxed to its tile so the game sorts it against
# lorries and neighbours; its company-colour cladding gets a mask. The bays are flat aprons drawn under the lorries.
# The game numbers the bays in their animation frame (src/station_cmd.cpp): 0-3 along the south-west face from north
# to south, 4-7 along the south-east face from north to south.
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from nml.palette import raw_palette_data

HERE = Path(__file__).resolve().parent
FL = HERE.parent
sys.path.insert(0, str(FL.parent / "tools"))
sys.path.insert(0, str(HERE))
import pixelart as P  # noqa: E402
from hub_model import HEIGHT, T, Scene, bay, facility, warehouse  # noqa: E402

GFX = FL / "gfx"
DOS = bytes(raw_palette_data[0])
CC_BASE = 198  # first company-colour palette index; 202 is its middle shade
ZEXTENT = 88  # up to the office tower's mast
BEGIN = "/* BEGIN generated Distribution Centre tiles (tools/make_distribution_hub.py) */"
END = "/* END generated Distribution Centre tiles */"


def sheet(name, pieces, zoom, masked):
    """Save pieces [(rgba, mask_or_None, xrel, yrel)] side by side; return the NML spriteset lines."""
    width = sum(p[0].width + 1 for p in pieces)
    height = max(p[0].height for p in pieces)
    strip = Image.new("RGBA", (width, height))
    mstrip = Image.new("P", (width, height))
    mstrip.putpalette(DOS)
    rows, x = [], 0
    for img, mask, xrel, yrel in pieces:
        a = np.asarray(img).copy()
        if mask is not None:
            m = (np.asarray(mask) > 0) & (a[..., 3] > 0)
            grey = a[..., :3].max(-1)
            for c in range(3):
                a[..., c][m] = grey[m]
            mi = np.zeros(m.shape, np.uint8)
            mi[m] = CC_BASE + 4
            part = Image.fromarray(mi, "P")
            part.putpalette(DOS)
            mstrip.paste(part, (x, 0))
        strip.alpha_composite(Image.fromarray(a), (x, 0))
        rows.append(f"    [{x}, 0, {img.width}, {img.height}, {xrel}, {yrel}]")
        x += img.width + 1
    file = f"gfx/{name}_{zoom}x.png"
    strip.save(FL / file)
    mask_arg = ""
    if masked:
        mstrip.save(FL / f"gfx/{name}_{zoom}x_mask.png")
        mask_arg = f', "gfx/{name}_{zoom}x_mask.png"'
    head = "spriteset" if zoom == 1 else "alternative_sprites"
    level = "ZOOM_LEVEL_NORMAL" if zoom == 1 else "ZOOM_LEVEL_IN_2X"
    return [f'{head}({name}, {level}, BIT_DEPTH_32BPP, "{file}"{mask_arg}) {{'] + rows + ["}"]


def warehouse_pieces(zoom):
    s = Scene()
    warehouse(s)
    img, mask, (ox, oy) = s.render(zoom=zoom)
    north = (-ox, -oy)
    pieces = P.slice_footprint(img, 4, 4, north, zoom)
    # The mask goes through the same cut: same pixels, same boxes.
    carrier = Image.merge("RGBA", (mask, mask, mask, img.getchannel("A")))
    mask_pieces = P.slice_footprint(carrier, 4, 4, north, zoom)
    order = [(x, y) for y in range(4) for x in range(4)]
    return [(pieces[k][0], mask_pieces[k][0].getchannel("R"), pieces[k][1], pieces[k][2]) for k in order]


def bay_pieces(zoom):
    out = []
    for axis in ("x", "y"):
        for i in range(4):
            s = Scene()
            bay(s, 0, 0, axis)
            img, mask, (ox, oy) = s.render(zoom=zoom)
            out.append((img, None, ox, oy))
    return out


def preview(zoom):
    img, mask, _ = facility().render(zoom=1)
    a = np.asarray(img).copy()
    m = np.asarray(mask) > 0
    a[m, 0], a[m, 1], a[m, 2] = 200, 50, 40  # a company colour for the picture in the construction windows
    img = Image.fromarray(a)
    w = 128 * zoom
    img = img.resize((w, round(img.height * w / img.width)), Image.Resampling.LANCZOS)
    return [(img, None, -img.width // 2, -img.height // 2)]


def main():
    lines = [BEGIN]
    for zoom in (1, 2):
        lines += sheet("distribution_hub_tiles", warehouse_pieces(zoom), zoom, True)
    for zoom in (1, 2):
        lines += sheet("distribution_hub_bays", bay_pieces(zoom), zoom, False)
    for zoom in (1, 2):
        lines += sheet("distribution_hub_preview", preview(zoom), zoom, False)
    for y in range(4):
        for x in range(4):
            i = y * 4 + x
            lines.append(f"spritelayout distribution_hub_tile_{x}_{y} {{ ground {{ sprite: GROUNDSPRITE_CONCRETE; }} "
                         f"building {{ sprite: distribution_hub_tiles({i}); xoffset: 0; yoffset: 0; zoffset: 0; "
                         f"xextent: 16; yextent: 16; zextent: {ZEXTENT}; recolour_mode: RECOLOUR_REMAP; palette: PALETTE_USE_DEFAULT; }} }}")
    for i in range(8):
        lines.append(f"spritelayout distribution_hub_bay_{i} {{ ground {{ sprite: GROUNDSPRITE_CONCRETE; }} "
                     f"childsprite {{ sprite: distribution_hub_bays({i}); }} }}")
    lines.append("spritelayout distribution_hub_layout { ground { sprite: GROUNDSPRITE_CONCRETE; } "
                 "childsprite { sprite: distribution_hub_preview(0); } }")
    cases = " ".join(f"0x{(y << 8) | x:04X}: distribution_hub_tile_{x}_{y};" for y in range(4) for x in range(4))
    lines.append(f"switch(FEAT_OBJECTS, SELF, distribution_hub_object_graphics, relative_pos) {{ {cases} distribution_hub_tile_0_0; }}")
    cases = " ".join(f"{i}: distribution_hub_bay_{i};" for i in range(8))
    lines.append(f"switch(FEAT_ROADSTOPS, SELF, distribution_hub_bay_graphics, animation_frame) {{ {cases} distribution_hub_bay_0; }}")
    lines.append(END)
    nml = FL / "future_logistics.nml"
    text = nml.read_text()
    a, b = text.index(BEGIN), text.index(END) + len(END)
    nml.write_text(text[:a] + "\n".join(lines) + text[b:])
    print("wrote the Distribution Centre: 16 warehouse tiles, 8 bays and a preview at two zoom levels")


if __name__ == "__main__":
    main()
