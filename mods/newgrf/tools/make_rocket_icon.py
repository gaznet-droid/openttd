#!/usr/bin/env python3
# GPL-2.0-only. Draws the small side-on rocket shown in the purchase list, depot and vehicle lists. Needs Pillow.
#
#   python3 mods/newgrf/tools/make_rocket_icon.py
#
# The rocket on the map is an upright sprite well over a hundred pixels tall: in a list row only its bottom showed.
# Lists get this instead, a Starship lying on its side with its nose to the right, drawn pixel by pixel at the
# base game's pixel size (and doubled for 2x zoom), and written into both NewGRFs that have a rocket.
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = [HERE.parent / "starship" / "gfx", HERE.parent / "future_logistics" / "gfx"]

W, H = 40, 13
MID = 6  # centre row
# Colours: the steel booster, the dark ship and the flame.
STEEL = [(120, 124, 130), (168, 172, 178), (206, 210, 214), (232, 234, 236), (190, 194, 198), (140, 144, 150), (96, 100, 106)]
SHIP = [(30, 32, 36), (52, 54, 60), (74, 78, 84), (92, 96, 104), (66, 70, 76), (44, 46, 52), (24, 26, 30)]
OUTLINE = (16, 16, 20)
FLAME = [(255, 244, 180), (255, 196, 64), (240, 110, 30)]


def draw():
    img = Image.new("RGBA", (W, H))
    px = img.load()

    def put(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            px[x, y] = (*c, 255)

    def body(x0, x1, half, ramp):
        """A cylinder from x0 to x1, half rows either side of the centre, shaded top to bottom."""
        for x in range(x0, x1):
            for dy in range(-half, half + 1):
                shade = ramp[min(len(ramp) - 1, (dy + half) * len(ramp) // (2 * half + 1))]
                put(x, MID + dy, shade)
            put(x, MID - half - 1, OUTLINE)
            put(x, MID + half + 1, OUTLINE)

    # Engine flame and bells at the tail.
    for i, c in enumerate(FLAME):
        for dy in range(-2 + i // 2, 3 - i // 2):
            put(i, MID + dy, c)
    for dy in (-2, 0, 2):
        put(3, MID + dy, (80, 80, 84))
        put(4, MID + dy, (110, 110, 116))
    # Super Heavy booster: steel, with grid fins near its top.
    body(5, 22, 3, STEEL)
    for x in (18, 19):
        put(x, MID - 5, (90, 94, 100))
        put(x, MID + 5, (90, 94, 100))
    put(5, MID - 4, OUTLINE)
    put(5, MID + 4, OUTLINE)
    # Hot-stage ring.
    for dy in range(-3, 4):
        put(22, MID + dy, (60, 62, 68))
    # Starship: dark steel with rear flaps, then the nose cone with its forward flaps.
    body(23, 32, 3, SHIP)
    for x in range(23, 27):
        put(x, MID - 5, (40, 42, 48))
        put(x, MID + 5, (40, 42, 48))
    for x in range(24, 26):
        put(x, MID - 6, OUTLINE)
        put(x, MID + 6, OUTLINE)
    nose = [(32, 3), (33, 3), (34, 2), (35, 2), (36, 1), (37, 1), (38, 0)]
    for x, half in nose:
        for dy in range(-half, half + 1):
            put(x, MID + dy, SHIP[min(6, (dy + half) * 7 // (2 * half + 1))])
        put(x, MID - half - 1, OUTLINE)
        put(x, MID + half + 1, OUTLINE)
    put(39, MID, OUTLINE)
    for x in (30, 31):
        put(x, MID - 4, (40, 42, 48))
        put(x, MID + 4, (40, 42, 48))
    # A highlight along the ship, the way the base game's planes catch the light.
    for x in range(24, 34, 2):
        put(x, MID - 2, (120, 126, 136))
    return img


def main():
    icon = draw()
    for folder in OUT:
        icon.save(folder / "rocket_icon_1x.png")
        icon.resize((W * 2, H * 2), Image.NEAREST).save(folder / "rocket_icon_2x.png")
    print(f"wrote {W}x{H} rocket icon to", ", ".join(str(f) for f in OUT))


if __name__ == "__main__":
    main()
