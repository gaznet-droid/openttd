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
#   pad_empty_{z}x.png, pad_docked_{z}x.png    the whole pad, with the tall hangar (spaceport_hangar.py), before slicing
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
import spaceport_hangar as H  # noqa: E402

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


MOUNT = (21, 36)  # launch mount in sixteenths of a tile from the footprint's north corner (src/future_logistics/orbital.h)
ROTOR_Z = 5  # a helicopter's rotor is drawn this many pixels above its body (aircraft.h)
GROUND_Z = 1  # the orbital controller stands the rocket one pixel above the ground (orbital.cpp)
EDGE = (104, 104, 102, 255)  # fill for any ground pixel inside the footprint the art does not reach

# Each GRF that defines the spaceport: its folder, NML file, sprite file prefix, NML name prefix and first airport tile ID.
TARGETS = [
    ("starship", "starship.nml", "pad", "pad", 0, "starship_pad_layout"),
    ("future_logistics", "future_logistics.nml", "orbital_pad", "orbital_pad", 16, "orbital_spaceport_layout"),
]
BEGIN, END = "/* BEGIN generated spaceport pad (tools/make_spaceport_art.py) */", "/* END generated spaceport pad */"


def sprite_line(kind, name, zoom, path, m):
    level = "ZOOM_LEVEL_NORMAL" if zoom == 1 else "ZOOM_LEVEL_IN_2X"
    head = "spriteset" if zoom == 1 else "alternative_sprites"
    return f'{head}({name}, {level}, BIT_DEPTH_32BPP, "gfx/{path}") {{ [0, 0, {m[0]}, {m[1]}, {m[2]}, {m[3]}] }}'


def main():
    empty = Image.open(ORIGINALS / "spaceport_empty_pad_transparent.png").convert("RGBA")
    docked = Image.open(ORIGINALS / "spaceport_starship_on_pad_transparent.png").convert("RGBA")
    powered = Image.open(POWERED).convert("RGBA")
    box = P.solid_bbox(powered, 40)
    powered = powered.crop(box)
    flame_start = (FLAME_START - box[1]) * POWERED_SCALE
    powered = powered.resize((round(powered.width * POWERED_SCALE), round(powered.height * POWERED_SCALE)), Image.BOX)
    rocket, rocket_at = cut_rocket(docked, empty)
    north_src = (WEST[0] + EAST[0] - SOUTH[0], WEST[1] + EAST[1] - SOUTH[1])
    tiles = {}   # (state, x, y, zoom) -> (image, xrel, yrel)
    rockets = {}  # zoom -> dict of rocket sprites and offsets
    preview = {}
    for zoom in (1, 2):
        f = source_per_pixel(zoom)
        north = (round((north_src[0] - CROP[0]) / f), round((north_src[1] - CROP[1]) / f))
        for state, image in (("e", empty), ("d", docked)):
            grid = to_grid(image.crop(CROP), zoom, 96)
            # The tall assembly hangar replaces the low one in the left-hand corner (tools/spaceport_hangar.py).
            grid, shift = H.overlay(grid, zoom, north)
            at_north = (north[0] + shift[0], north[1] + shift[1])
            for (x, y), (piece, xrel, yrel) in P.slice_footprint(grid, *FOOTPRINT, at_north, zoom, fill=EDGE).items():
                tiles[(state, x, y, zoom)] = (piece, xrel, yrel)
            if state == "d":
                pw = 96 * zoom
                preview[zoom] = P.pixelate(grid, pw, 64)
        # Rocket: placed so that, standing at the launch mount, it covers exactly the docked rocket in the pad art.
        idle = to_grid(rocket, zoom, 48)
        at = (round((rocket_at[0] - CROP[0]) / f), round((rocket_at[1] - CROP[1]) / f))
        mx, my = MOUNT
        vx = north[0] + 2 * (my - mx) * zoom
        vy = north[1] + (mx + my) * zoom - (GROUND_Z + ROTOR_Z) * zoom
        lit = to_grid(powered, zoom, 48)
        body_h = round(flame_start / f)
        frames = []
        for stretch in (1.0, 1.12, 0.9):
            flame = lit.crop((0, body_h, lit.width, lit.height))
            flame = flame.resize((flame.width, max(1, round(flame.height * stretch))), Image.NEAREST)
            img = Image.new("RGBA", (lit.width, body_h + flame.height))
            img.alpha_composite(lit.crop((0, 0, lit.width, body_h)))
            img.alpha_composite(flame, (0, body_h))
            frames.append(img)
        rockets[zoom] = {"idle": idle, "frames": frames,
                         "rotor_xrel": at[0] - vx - (lit.width - idle.width) // 2, "rotor_yrel": at[1] - vy,
                         "mount_screen": (vx, vy)}
        # Where the docked rocket's foot actually is, as a check on MOUNT.
        foot = (at[0] + idle.width / 2 - north[0], at[1] + idle.height - north[1])
        print(f"zoom {zoom}: rocket foot at screen {foot}, mount world ~ x={(foot[1] - foot[0] / 2) / 2 / zoom:.1f} y={(foot[1] + foot[0] / 2) / 2 / zoom:.1f}")

    for folder, nml, file_prefix, name_prefix, first_id, layout_name in TARGETS:
        gfx = NEWGRF / folder / "gfx"
        gfx.mkdir(exist_ok=True)
        lines = [BEGIN,
                 "/* The launch pad, 3x4 tiles, from the Corporate Infrastructure spaceport art in the base game's pixel density.",
                 " * Each tile draws its piece of the picture as a building with a tall box, so no tile draws over another and the",
                 " * tall parts sort correctly against neighbouring buildings. The pad shows Starship",
                 " * docked on its launch mount (animation frame 1, set by the orbital controller while a shuttle boards or is",
                 " * serviced) or empty with the tower arms swung open (frame 0). The layout turns the country airport, whose",
                 " * movement the spaceport uses, a quarter turn to fit the art's 3x4 footprint. */"]
        idx = 0
        layout_lines = [f"tilelayout {layout_name} {{ rotation: DIRECTION_EAST;"]
        for y in range(FOOTPRINT[1]):
            for x in range(FOOTPRINT[0]):
                names = {}
                for state in ("e", "d"):
                    sname = f"{name_prefix}_{state}_{x}_{y}"
                    for zoom in (1, 2):
                        piece, xrel, yrel = tiles[(state, x, y, zoom)]
                        path = f"{file_prefix}_{state}_{x}_{y}_{zoom}x.png"
                        piece.save(gfx / path)
                        lines.append(sprite_line(state, sname, zoom, path, (piece.width, piece.height, xrel, yrel)))
                    # A building sprite with a tall box over the whole tile, so the game's sprite sorter draws the pad's
                    # tall parts (tower, rocket, tanks) in front of buildings behind the pad and behind those in front.
                    lines.append(f"spritelayout {sname}_layout {{ ground {{ sprite: GROUNDSPRITE_CONCRETE; }} "
                                 f"building {{ sprite: {sname}(0); xextent: 16; yextent: 16; zextent: 160; }} }}")
                    names[state] = f"{sname}_layout"
                lines.append(f"switch (FEAT_AIRPORTTILES, SELF, {name_prefix}_switch_{x}_{y}, animation_frame) {{ 1: {names['d']}; {names['e']}; }}")
                lines.append(f"item(FEAT_AIRPORTTILES, {name_prefix}_tile_{x}_{y}, {first_id + idx}) {{ property {{ substitute: 0; }} graphics {{ default: {name_prefix}_switch_{x}_{y}; }} }}")
                layout_lines.append(f"    {x}, {y}: {name_prefix}_tile_{x}_{y};")
                idx += 1
        layout_lines.append("}")
        lines += layout_lines
        # Picker preview: the whole docked pad.
        for zoom in (1, 2):
            path = f"{file_prefix}_preview_{zoom}x.png"
            preview[zoom].save(gfx / path)
            img = preview[zoom]
            lines.append(sprite_line("p", f"{name_prefix}_preview", zoom, path, (img.width, img.height, -img.width // 2, -img.height // 2)))
        lines.append(END)
        text = (NEWGRF / folder / nml).read_text()
        a, b = text.index(BEGIN), text.index(END) + len(END)
        (NEWGRF / folder / nml).write_text(text[:a] + "\n".join(lines) + text[b:])
        print(f"{folder}: {idx} pad tiles")

    # Starship's own sprites, in the Starship GRF.
    gfx = NEWGRF / "starship" / "gfx"
    for zoom in (1, 2):
        r = rockets[zoom]
        r["idle"].save(gfx / f"starship_idle_{zoom}x.png")
        strip = Image.new("RGBA", (sum(fr.width + 1 for fr in r["frames"]), max(fr.height for fr in r["frames"])))
        x = 0
        boxes = []
        for fr in r["frames"]:
            strip.alpha_composite(fr, (x, 0))
            boxes.append((x, fr.width, fr.height))
            x += fr.width + 1
        strip.save(gfx / f"starship_lit_{zoom}x.png")
        r["boxes"] = boxes
    meta = {z: {"idle": list(rockets[z]["idle"].size), "lit": rockets[z]["boxes"],
                "rotor_xrel": rockets[z]["rotor_xrel"], "rotor_yrel": rockets[z]["rotor_yrel"]} for z in (1, 2)}
    (gfx / "starship_sprites.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
