#!/usr/bin/env python3
# GPL-2.0-only. Cuts the Distribution Centre picture into one piece per tile. Needs Pillow and NumPy.
#
#   python3 mods/newgrf/future_logistics/tools/slice_distribution_hub.py
#
# The picture covers the whole 4x4 facility: the 3x4 warehouse object and the 1x4 strip of truck bays on its
# south-west side. Drawn as one big sprite from a single tile, parts of it vanished whenever the game redrew only
# the area around a passing truck. Each tile now draws its own piece: the warehouse tiles as building sprites
# boxed to their tile, so the game sorts them against vehicles and buildings around them, and the flat bay aprons
# as ground child sprites under the trucks.
# The bays are road stops; the game numbers them 0-3 from north-west to south-east in their animation frame
# (src/station_cmd.cpp), and the road stop graphics pick the piece by that number.
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
FL = HERE.parent
sys.path.insert(0, str(FL.parent / "tools"))
import pixelart as P  # noqa: E402

TILES = (4, 4)  # x (down-left) by y (down-right); the bays are the x = 3 strip.
NORTH = {1: (128, 58), 2: (256, 117)}  # The facility's north corner in each picture (from the old sprite offsets).
HEIGHT = 56  # The warehouse's height in pixels at normal zoom, its object height.
BEGIN = "/* BEGIN generated Distribution Centre tiles (tools/slice_distribution_hub.py) */"
END = "/* END generated Distribution Centre tiles */"


def main():
    lines = [BEGIN]
    entries = {}
    for zoom in (1, 2):
        image = Image.open(FL / "gfx" / f"distribution_hub_{zoom}x.png").convert("RGBA")
        pieces = P.slice_footprint(image, *TILES, NORTH[zoom], zoom)
        order = [(x, y) for y in range(TILES[1]) for x in range(TILES[0])]
        sheet = Image.new("RGBA", (sum(pieces[k][0].width + 1 for k in order), max(pieces[k][0].height for k in order)))
        left = 0
        rows = []
        for k in order:
            piece, xrel, yrel = pieces[k]
            sheet.alpha_composite(piece, (left, 0))
            rows.append(f"[{left}, 0, {piece.width}, {piece.height}, {xrel}, {yrel}]")
            left += piece.width + 1
        name = f"gfx/distribution_hub_tiles_{zoom}x.png"
        sheet.save(FL / name)
        head = "spriteset(distribution_hub_tiles, ZOOM_LEVEL_NORMAL" if zoom == 1 else "alternative_sprites(distribution_hub_tiles, ZOOM_LEVEL_IN_2X"
        lines.append(f'{head}, BIT_DEPTH_32BPP, "{name}") {{')
        lines += [f"    {r}" for r in rows]
        lines.append("}")
        entries[zoom] = order
    order = entries[1]
    for x, y in order:
        i = order.index((x, y))
        if x < 3:
            # Warehouse tiles: a building sprite with the whole tile as its box, so the game sorts the building
            # against what stands behind or in front of it.
            lines.append(f"spritelayout distribution_hub_tile_{x}_{y} {{ ground {{ sprite: GROUNDSPRITE_CONCRETE; }} "
                         f"building {{ sprite: distribution_hub_tiles({i}); xoffset: 0; yoffset: 0; zoffset: 0; "
                         f"xextent: 16; yextent: 16; zextent: {HEIGHT}; }} }}")
        else:
            # Bay aprons are flat: drawn on the ground, under the trucks.
            lines.append(f"spritelayout distribution_hub_tile_{x}_{y} {{ ground {{ sprite: GROUNDSPRITE_CONCRETE; }} "
                         f"childsprite {{ sprite: distribution_hub_tiles({i}); }} }}")
    # Warehouse object: its tiles are x 0-2; relative_pos is (y << 8) | x.
    cases = " ".join(f"0x{(y << 8) | x:04X}: distribution_hub_tile_{x}_{y};" for x, y in order if x < 3)
    lines.append(f"switch(FEAT_OBJECTS, SELF, distribution_hub_object_graphics, relative_pos) {{ {cases} distribution_hub_tile_0_0; }}")
    # Bays: road stops numbered by their animation frame.
    cases = " ".join(f"{y}: distribution_hub_tile_3_{y};" for y in range(4))
    lines.append(f"switch(FEAT_ROADSTOPS, SELF, distribution_hub_bay_graphics, animation_frame) {{ {cases} distribution_hub_tile_3_0; }}")
    lines.append(END)
    nml = FL / "future_logistics.nml"
    text = nml.read_text()
    a, b = text.index(BEGIN), text.index(END) + len(END)
    nml.write_text(text[:a] + "\n".join(lines) + text[b:])
    print("wrote", len(order), "tiles at two zoom levels")


if __name__ == "__main__":
    main()
