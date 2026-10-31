#!/usr/bin/env python3
# GPL-2.0-only. Shared helpers that turn painterly "pixel art" source images into chunky OpenTTD sprites.
#
# The handoff art is drawn at about 1254 px with soft-edged blocks standing in for pixels. Smoothly
# downscaling it (LANCZOS) blends those blocks and loses the pixel-art look. Instead each image is snapped
# onto a coarse art grid, one colour per cell taken as the median of the cell's solid source pixels (so
# neighbouring blocks are never blended), the palette is reduced, stray edge pixels are cleaned up, and the
# grid is scaled up with nearest-neighbour only: by ART_SCALE game pixels per art pixel at normal zoom, and
# twice that at 2x zoom. Everything in the game set uses the same ART_SCALE, so all art shares one pixel size.
#
# In OpenTTD's view a tile's x axis runs down and to the left and its y axis down and to the right; a tile's
# ground diamond is TILE_W x TILE_H pixels at normal zoom.
from PIL import Image
import numpy as np

TILE_W, TILE_H = 64, 32
ART_SCALE = 1  # Game pixels per art pixel at normal zoom (2 at 2x zoom): the base game's pixel density.


def solid_bbox(image, threshold=128):
    """Bounding box of the pixels at least `threshold` opaque."""
    return image.getchannel("A").point(lambda a: 255 if a >= threshold else 0).getbbox()


def snap_to_grid(image, grid_w, grid_h=None, coverage=0.5, solid=160):
    """Snap an RGBA image onto a grid_w-wide art grid (grid_h follows the aspect ratio unless given).

    A cell is opaque when at least `coverage` of its source pixels are solid (alpha >= `solid`); its colour is the
    per-channel median of those solid pixels."""
    src = np.asarray(image.convert("RGBA"))
    h, w = src.shape[:2]
    if grid_h is None:
        grid_h = max(1, round(h * grid_w / w))
    xs = np.linspace(0, w, grid_w + 1).round().astype(int)
    ys = np.linspace(0, h, grid_h + 1).round().astype(int)
    out = np.zeros((grid_h, grid_w, 4), np.uint8)
    for j in range(grid_h):
        band = src[ys[j]:ys[j + 1]]
        for i in range(grid_w):
            cell = band[:, xs[i]:xs[i + 1]].reshape(-1, 4)
            if cell.size == 0:
                continue
            opaque = cell[cell[:, 3] >= solid]
            if len(opaque) < coverage * len(cell):
                continue
            out[j, i, :3] = np.median(opaque[:, :3], axis=0)
            out[j, i, 3] = 255
    return Image.fromarray(out, "RGBA")


def reduce_palette(grid, colours=64):
    """Reduce the opaque cells to at most `colours` colours, without dithering."""
    rgb = grid.convert("RGB")
    q = rgb.quantize(colors=colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    return Image.merge("RGBA", (*q.split(), grid.getchannel("A")))


def clean(grid, passes=1):
    """Drop single opaque cells with no opaque 4-neighbours, and fill single holes surrounded on all four sides."""
    a = np.asarray(grid).copy()
    for _ in range(passes):
        op = a[..., 3] > 0
        p = np.pad(op, 1)
        n = p[:-2, 1:-1].astype(int) + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
        a[op & (n == 0), 3] = 0
        holes = ~op & (n == 4)
        if holes.any():
            # Fill a hole with the colour of its upper neighbour.
            up = np.roll(a, 1, axis=0)
            a[holes] = up[holes]
            a[holes, 3] = 255
    return Image.fromarray(a, "RGBA")


def pixelate(image, grid_w, colours=64, grid_h=None):
    """The whole pipeline from a source image to its art grid."""
    return clean(reduce_palette(snap_to_grid(image, grid_w, grid_h), colours))


def upscale(grid, zoom):
    """Scale an art grid to game pixels: zoom 1 is normal zoom, zoom 2 the 2x zoom level."""
    f = ART_SCALE * zoom
    return grid.resize((grid.width * f, grid.height * f), Image.NEAREST)


def slice_footprint(image, tiles_x, tiles_y, north, zoom, fill=None):
    """Cut a footprint image into one ground piece per tile, so no tile draws over another.

    `north` is the screen position of the footprint's north corner in `image`. Every pixel goes to exactly one
    tile: the tile it would lie on if it were on the ground. Uncovered ground is left transparent unless `fill`
    is given. Returns {(x, y): (piece, xrel, yrel)} with offsets from each tile's own north corner."""
    tw, th = TILE_W * zoom, TILE_H * zoom
    nx, ny = north
    left = min(0, nx - tiles_y * tw // 2)
    top = min(0, ny)
    right = max(image.width, nx + tiles_x * tw // 2)
    bottom = max(image.height, ny + (tiles_x + tiles_y) * th // 2)
    canvas = Image.new("RGBA", (right - left, bottom - top))
    canvas.alpha_composite(image.convert("RGBA"), (-left, -top))
    nx, ny = nx - left, ny - top
    src = np.asarray(canvas)
    yy, xx = np.mgrid[0:canvas.height, 0:canvas.width]
    sx = (xx + 0.5 - nx) / (tw / 2)
    sy = (yy + 0.5 - ny) / (th / 2)
    u = (sy + sx) / 2  # along the y axis, down and to the right
    v = (sy - sx) / 2  # along the x axis, down and to the left
    on_ground = (v >= 0) & (v < tiles_x) & (u >= 0) & (u < tiles_y)
    tx = np.clip(np.floor(v), 0, tiles_x - 1).astype(int)
    ty = np.clip(np.floor(u), 0, tiles_y - 1).astype(int)
    pieces = {}
    for x in range(tiles_x):
        for y in range(tiles_y):
            mine = (tx == x) & (ty == y)
            px = np.zeros_like(src)
            px[mine] = src[mine]
            if fill is not None:
                bare = mine & on_ground & (src[..., 3] == 0)
                px[bare] = fill
            piece = Image.fromarray(px, "RGBA")
            box = piece.getbbox()
            if box is None:
                box = (0, 0, 1, 1)
            tile_x = nx + (y - x) * tw // 2
            tile_y = ny + (x + y) * th // 2
            pieces[(x, y)] = (piece.crop(box), box[0] - tile_x, box[1] - tile_y)
    return pieces
