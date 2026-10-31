#!/usr/bin/env python3
# GPL-2.0-only. A small isometric pixel renderer for drawing NewGRF art in code. Needs NumPy and Pillow.
#
# Shapes are built from triangles in OpenTTD's world coordinates: x runs down and to the left on screen, y
# down and to the right, z up. A tile is 16 units each way and one height level is 8 units. At normal zoom
# a point projects to screen (2 * (y - x), (x + y) - z), so a tile's ground diamond is 64 x 32 pixels, the
# game's own geometry. Triangles are filled with a depth buffer and no anti-aliasing, faces are flat-shaded
# from their normals, and silhouettes and creases get darker outlines, so the result reads like the game's
# hand-drawn pixel art. A material may be marked as company colour: its pixels are also written to a mask
# so the game can recolour them for the owning company.
import math

import numpy as np
from PIL import Image

LIGHT = np.array([0.55, 0.15, 1.0])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


class Material:
    def __init__(self, rgb, shade=True, company=False, glow=False):
        self.rgb = np.array(rgb, float)
        self.shade = shade and not glow
        self.company = company
        self.glow = glow


class Scene:
    def __init__(self):
        self.tris = []  # (p0, p1, p2, material)

    # --- building blocks -------------------------------------------------------------------------------------
    def tri(self, a, b, c, m):
        self.tris.append((np.array(a, float), np.array(b, float), np.array(c, float), m))

    def quad(self, a, b, c, d, m):
        self.tri(a, b, c, m)
        self.tri(a, c, d, m)

    def box(self, x0, y0, z0, x1, y1, z1, m, top=None, sides=None):
        top = top or m
        sides = sides or m
        p = lambda x, y, z: (x, y, z)  # noqa: E731
        self.quad(p(x0, y0, z1), p(x1, y0, z1), p(x1, y1, z1), p(x0, y1, z1), top)  # top
        self.quad(p(x1, y0, z0), p(x1, y1, z0), p(x1, y1, z1), p(x1, y0, z1), sides)  # +x face
        self.quad(p(x0, y1, z0), p(x1, y1, z0), p(x1, y1, z1), p(x0, y1, z1), sides)  # +y face
        self.quad(p(x0, y0, z0), p(x0, y1, z0), p(x0, y1, z1), p(x0, y0, z1), sides)  # -x face
        self.quad(p(x0, y0, z0), p(x1, y0, z0), p(x1, y0, z1), p(x0, y0, z1), sides)  # -y face

    def prism(self, axis, start, end, centre, profile, m, caps=True, mats=None):
        """Extrude a closed 2D profile [(u, z), ...] along axis 'x' or 'y' from start to end.

        centre is (c, zc): the profile's u is across the axis (y for an x prism, x for a y prism)."""
        c, zc = centre
        def pt(t, u, z):
            return (t, c + u, zc + z) if axis == "x" else (c + u, t, zc + z)
        n = len(profile)
        for i in range(n):
            (u0, z0), (u1, z1) = profile[i], profile[(i + 1) % n]
            mm = mats[i] if mats else m
            self.quad(pt(start, u0, z0), pt(end, u0, z0), pt(end, u1, z1), pt(start, u1, z1), mm)
        if caps:
            for t in (start, end):
                for i in range(1, n - 1):
                    self.tri(pt(t, *profile[0]), pt(t, *profile[i]), pt(t, *profile[i + 1]), m)

    def cylinder(self, x, y, z0, z1, r, m, sides=10):
        prof = [(r * math.cos(2 * math.pi * i / sides), r * math.sin(2 * math.pi * i / sides)) for i in range(sides)]
        for i in range(sides):
            (a0, b0), (a1, b1) = prof[i], prof[(i + 1) % sides]
            self.quad((x + a0, y + b0, z0), (x + a1, y + b1, z0), (x + a1, y + b1, z1), (x + a0, y + b0, z1), m)
        for i in range(1, sides - 1):
            self.tri((x + prof[0][0], y + prof[0][1], z1), (x + prof[i][0], y + prof[i][1], z1),
                     (x + prof[i + 1][0], y + prof[i + 1][1], z1), m)

    # --- rendering ---------------------------------------------------------------------------------------------
    def render(self, zoom=1, origin=None, size=None, outline=0.55, crease=0.75):
        """Render to (RGBA image, company mask, (xrel, yrel)).

        The world origin (0, 0, 0) is the north corner of tile (0, 0); xrel/yrel give the image's top-left corner
        relative to it in screen pixels, as NewGRF sprite offsets want."""
        s = zoom
        proj = lambda p: (2 * s * (p[1] - p[0]), s * (p[0] + p[1]) - s * p[2])  # noqa: E731
        pts = [np.array([proj(p) for p in t[:3]]) for t in self.tris]
        allp = np.vstack(pts)
        if origin is None:
            ox, oy = math.floor(allp[:, 0].min()) - 2, math.floor(allp[:, 1].min()) - 2
            w, h = math.ceil(allp[:, 0].max()) - ox + 3, math.ceil(allp[:, 1].max()) - oy + 3
        else:
            (ox, oy), (w, h) = origin, size
        col = np.zeros((h, w, 3))
        alpha = np.zeros((h, w), bool)
        depth = np.full((h, w), -1e9)
        mask = np.zeros((h, w), bool)
        ident = np.full((h, w), -1, int)
        for k, ((a, b, c, m), sp) in enumerate(zip(self.tris, pts)):
            n = np.cross(b - a, c - a)
            ln = np.linalg.norm(n)
            if ln == 0:
                continue
            n = n / ln
            view = np.array([1.0, 1.0, 2.0])
            if np.dot(n, view) < 0:
                n = -n  # double-sided: shade the face we see
            if m.glow:
                rgb = m.rgb
            elif m.shade:
                rgb = m.rgb * (0.66 + 0.40 * max(0.0, float(np.dot(n, LIGHT))))
            else:
                rgb = m.rgb
            sp = sp - (ox, oy)
            x0, x1 = max(0, int(math.floor(sp[:, 0].min()))), min(w - 1, int(math.ceil(sp[:, 0].max())))
            y0, y1 = max(0, int(math.floor(sp[:, 1].min()))), min(h - 1, int(math.ceil(sp[:, 1].max())))
            if x0 > x1 or y0 > y1:
                continue
            yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            px, py = xx + 0.5, yy + 0.5
            (ax, ay), (bx, by), (cx, cy) = sp
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9:
                continue
            l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / den
            l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / den
            l3 = 1 - l1 - l2
            inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            if not inside.any():
                continue
            dw = np.array([p[0] + p[1] + 2 * p[2] for p in (a, b, c)])
            d = l1 * dw[0] + l2 * dw[1] + l3 * dw[2]
            sub_d = depth[y0:y1 + 1, x0:x1 + 1]
            win = inside & (d > sub_d + 1e-6)
            sub_d[win] = d[win]
            col[y0:y1 + 1, x0:x1 + 1][win] = rgb
            alpha[y0:y1 + 1, x0:x1 + 1][win] = True
            mask[y0:y1 + 1, x0:x1 + 1][win] = m.company
            ident[y0:y1 + 1, x0:x1 + 1][win] = id(m) % 100000 * 1000 + (0 if m.glow else int(abs(n[0]) * 9) * 100 + int(abs(n[1]) * 9) * 10 + int(abs(n[2]) * 9))
        # Outlines: silhouette pixels and creases between differently facing surfaces get darker.
        out = col.copy()
        pad_a = np.pad(alpha, 1)
        edge = alpha & ~(pad_a[:-2, 1:-1] & pad_a[2:, 1:-1] & pad_a[1:-1, :-2] & pad_a[1:-1, 2:])
        out[edge] *= outline
        pid = np.pad(ident, 1, constant_values=-1)
        pdep = np.pad(depth, 1, constant_values=-1e9)
        creased = np.zeros_like(alpha)
        for dy, dx in ((1, 0), (0, 1)):
            nb_id = pid[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            nb_d = pdep[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            creased |= alpha & (nb_id >= 0) & ((nb_id != ident) & (np.abs(nb_d - depth) > 2.5))
        out[creased & ~edge] *= crease
        rgba = np.dstack([np.clip(out, 0, 255), alpha * 255]).astype(np.uint8)
        return Image.fromarray(rgba, "RGBA"), Image.fromarray((mask * 255).astype(np.uint8), "L"), (ox, oy)


def recolour(image, mask, rgb):
    """Preview a company colour: tint the masked pixels towards rgb, keeping their shading."""
    a = np.asarray(image).astype(float)
    m = np.asarray(mask) > 0
    lum = a[..., :3].mean(-1, keepdims=True) / 200.0
    tinted = np.clip(np.array(rgb, float)[None, None, :] * lum, 0, 255)
    a[..., :3][m] = tinted[m]
    return Image.fromarray(a.astype(np.uint8), "RGBA")
