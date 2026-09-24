from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

W, H = 1290, 2796

# Six visible stages: five rounded-rectangle rings plus a center disc.
# Fewer, broader steps read much more like the supplied recessed reference.
COLORS = [
    (18, 86, 75, 255),
    (27, 112, 94, 255),
    (39, 143, 117, 255),
    (56, 175, 141, 255),
    (82, 205, 169, 255),
    (137, 229, 204, 255),
]

BOXES = [
    (76, 700, W - 76, 2230, 170),
    (135, 790, W - 135, 2140, 150),
    (210, 900, W - 210, 2030, 130),
    (300, 1030, W - 300, 1900, 108),
    (405, 1180, W - 405, 1750, 82),
]
CENTER = (W // 2, 1465, 165)

# The outer/top stage is nearly screen-sized and moves least.
# Deeper-looking stages have progressively more hidden border available.
OVERSCANS = [1.035, 1.055, 1.085, 1.12, 1.17, 1.24]
BACKGROUND_OVERSCAN = 1.32


def _expanded_canvas(scale: float) -> tuple[Image.Image, int, int]:
    cw = int(math.ceil(W * scale))
    ch = int(math.ceil(H * scale))
    ox = (cw - W) // 2
    oy = (ch - H) // 2
    return Image.new("RGBA", (cw, ch), (0, 0, 0, 0)), ox, oy


def make_background(scale: float = BACKGROUND_OVERSCAN) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    draw = ImageDraw.Draw(canvas)
    cw, ch = canvas.size
    for y in range(ch):
        t = min(1.0, max(0.0, (y - oy) / max(H - 1, 1)))
        c = (7 + int(4 * t), 48 + int(8 * t), 42 + int(6 * t), 255)
        draw.line((0, y, cw, y), fill=c)

    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = ox + W // 2, oy + 1465
    gd.ellipse((cx - 460, cy - 460, cx + 460, cy + 460), fill=(95, 245, 220, 14))
    glow = glow.filter(ImageFilter.GaussianBlur(150))
    return Image.alpha_composite(canvas, glow)


def _inner_mask(size, ox: int, oy: int, inner_shape) -> Image.Image:
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    if inner_shape[0] == "rounded":
        _, ix0, iy0, ix1, iy1, ir = inner_shape
        d.rounded_rectangle(
            (ox + ix0, oy + iy0, ox + ix1, oy + iy1),
            radius=ir,
            fill=255,
        )
    else:
        _, cx, cy, rr = inner_shape
        d.ellipse(
            (ox + cx - rr, oy + cy - rr, ox + cx + rr, oy + cy + rr),
            fill=255,
        )
    return mask


def ring_slice(outer_box, inner_shape, color, scale: float) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)

    ring_alpha = Image.new("L", canvas.size, 0)
    ad = ImageDraw.Draw(ring_alpha)
    x0, y0, x1, y1, radius = outer_box
    ad.rounded_rectangle(
        (ox + x0, oy + y0, ox + x1, oy + y1),
        radius=radius,
        fill=255,
    )

    hole = _inner_mask(canvas.size, ox, oy, inner_shape)
    # Punch the hole out of the ring.
    ring_alpha = Image.subtract(ring_alpha, hole)

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(ring_alpha)

    # Darken the ring immediately around the inner edge. This cue is important:
    # it makes the nested shapes read as a cavity even though the parallax motion
    # is deliberately non-physical (deeper-looking stages move more).
    blurred_hole = hole.filter(ImageFilter.GaussianBlur(26))
    shadow_alpha = Image.new("L", canvas.size, 0)
    sa = shadow_alpha.load()
    bh = blurred_hole.load()
    ra = ring_alpha.load()
    for y in range(canvas.height):
        for x in range(canvas.width):
            if ra[x, y]:
                sa[x, y] = int(min(82, bh[x, y] * 0.42))

    shadow = Image.new("RGBA", canvas.size, (0, 22, 18, 255))
    shadow.putalpha(shadow_alpha)
    return Image.alpha_composite(layer, shadow)


def center_circle(color, scale: float) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    cx, cy, radius = CENTER
    cx += ox
    cy += oy

    alpha = Image.new("L", canvas.size, 0)
    ad = ImageDraw.Draw(alpha)
    ad.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(alpha)

    highlight = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.ellipse((cx - 118, cy - 118, cx + 118, cy + 118), fill=(255, 255, 255, 26))
    highlight = highlight.filter(ImageFilter.GaussianBlur(34))
    highlight.putalpha(Image.composite(highlight.getchannel("A"), Image.new("L", canvas.size, 0), alpha))
    return Image.alpha_composite(layer, highlight)


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale slices from previous layer-count experiments.
    for old in out_dir.glob("slice_*.png"):
        old.unlink()

    make_background().save(out_dir / "background.png")

    for i, outer in enumerate(BOXES):
        if i + 1 < len(BOXES):
            inner = ("rounded",) + BOXES[i + 1]
        else:
            inner = ("circle",) + CENTER
        ring_slice(outer, inner, COLORS[i], OVERSCANS[i]).save(
            out_dir / f"slice_{i:02d}.png"
        )

    center_circle(COLORS[-1], OVERSCANS[-1]).save(
        out_dir / f"slice_{len(BOXES):02d}.png"
    )
    print(f"Generated {len(BOXES) + 1} slices + background in {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/layered_assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
