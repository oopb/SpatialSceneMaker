from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H = 1290, 2796

# Six visible stages:
# five full-screen cut-out plates + one full-screen bottom image.
#
# Every slice has the same outer extent. The nested geometry is created only by
# punching progressively smaller holes through the plates above it.
COLORS = [
    (18, 86, 75, 255),
    (27, 112, 94, 255),
    (39, 143, 117, 255),
    (56, 175, 141, 255),
    (82, 205, 169, 255),
    (137, 229, 204, 255),
]

# Opening sizes restored from the earlier six-stage version.
ROUNDED_HOLES = [
    (135, 790, W - 135, 2140, 150),
    (210, 900, W - 210, 2030, 130),
    (300, 1030, W - 300, 1900, 108),
    (405, 1180, W - 405, 1750, 82),
]
CENTER = (W // 2, 1465, 165)

# Restore the earlier sharp asset layout. Upper layers keep only a small hidden
# margin, while deeper layers get progressively more safety area for parallax.
# This preserves substantially more effective texture resolution on the upper
# visible layers than forcing every slice to the deepest-layer overscan.
OVERSCANS = [1.035, 1.055, 1.085, 1.12, 1.17, 1.24]
BACKGROUND_OVERSCAN = 1.32


def _expanded_canvas(scale: float) -> tuple[Image.Image, int, int]:
    cw = int(math.ceil(W * scale))
    ch = int(math.ceil(H * scale))
    ox = (cw - W) // 2
    oy = (ch - H) // 2
    return Image.new("RGBA", (cw, ch), (0, 0, 0, 0)), ox, oy


def _rounded_mask(size, ox: int, oy: int, box) -> Image.Image:
    x0, y0, x1, y1, radius = box
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle(
        (ox + x0, oy + y0, ox + x1, oy + y1),
        radius=radius,
        fill=255,
    )
    return mask


def _circle_mask(size, ox: int, oy: int, circle) -> Image.Image:
    cx, cy, radius = circle
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.ellipse(
        (ox + cx - radius, oy + cy - radius, ox + cx + radius, oy + cy + radius),
        fill=255,
    )
    return mask


def _shape_mask(size, ox: int, oy: int, shape) -> Image.Image:
    if shape[0] == "rounded":
        return _rounded_mask(size, ox, oy, shape[1:])
    if shape[0] == "circle":
        return _circle_mask(size, ox, oy, shape[1:])
    raise ValueError(f"unknown shape: {shape[0]}")


def _full_surface_alpha(size) -> Image.Image:
    return Image.new("L", size, 255)


def make_background(scale: float = BACKGROUND_OVERSCAN) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    draw = ImageDraw.Draw(canvas)
    cw, ch = canvas.size

    for y in range(ch):
        t = min(1.0, max(0.0, (y - oy) / max(H - 1, 1)))
        c = (7 + int(4 * t), 48 + int(8 * t), 42 + int(6 * t), 255)
        draw.line((0, y, cw, y), fill=c)

    return canvas


def _soft_hole_highlight(
    hole: Image.Image,
    visible_alpha: Image.Image,
) -> Image.Image:
    # Restore the previous lighting direction: the CURRENT plate brightens
    # softly as it approaches its own cut-out edge.
    #
    # Two blur scales give a natural long transition plus a slightly stronger
    # near-edge increment without introducing any dark shadow.
    broad = hole.filter(ImageFilter.GaussianBlur(58)).point(
        lambda p: min(18, int(p * 0.07))
    )
    near = hole.filter(ImageFilter.GaussianBlur(17)).point(
        lambda p: min(42, int(p * 0.17))
    )

    alpha = ImageChops.add(broad, near)
    alpha = ImageChops.multiply(alpha, visible_alpha)

    highlight = Image.new("RGBA", hole.size, (228, 255, 248, 255))
    highlight.putalpha(alpha)
    return highlight


def plate_slice(
    hole_shape,
    color,
    scale: float,
) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)

    surface_alpha = _full_surface_alpha(canvas.size)
    hole = _shape_mask(canvas.size, ox, oy, hole_shape)
    visible_alpha = ImageChops.subtract(surface_alpha, hole)

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(visible_alpha)

    # Brighten the current plate toward its own hole edge.
    return Image.alpha_composite(
        layer,
        _soft_hole_highlight(hole, visible_alpha),
    )


def bottom_surface(
    color,
    scale: float,
) -> Image.Image:
    # The deepest stage is also a full-screen image. It remains fully opaque;
    # the circular appearance comes only from the cut-out in the layer above.
    canvas, ox, oy = _expanded_canvas(scale)
    layer = Image.new("RGBA", canvas.size, color)

    cx, cy, _ = CENTER
    cx += ox
    cy += oy

    # Keep the same soft center lift used before the lighting-direction change.
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    radius = 360
    gd.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=(255, 255, 255, 18),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(125))

    return Image.alpha_composite(layer, glow)


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for old in out_dir.glob("slice_*.png"):
        old.unlink()

    make_background().save(out_dir / "background.png")

    rounded_shapes = [("rounded",) + hole for hole in ROUNDED_HOLES]
    circle_shape = ("circle",) + CENTER

    for i, shape in enumerate(rounded_shapes):
        plate_slice(
            shape,
            COLORS[i],
            OVERSCANS[i],
        ).save(out_dir / f"slice_{i:02d}.png")

    plate_slice(
        circle_shape,
        COLORS[len(rounded_shapes)],
        OVERSCANS[len(rounded_shapes)],
    ).save(out_dir / f"slice_{len(rounded_shapes):02d}.png")

    bottom_surface(
        COLORS[-1],
        OVERSCANS[-1],
    ).save(out_dir / f"slice_{len(rounded_shapes) + 1:02d}.png")

    print(
        f"Generated {len(rounded_shapes) + 2} full-screen slices + background "
        f"in {out_dir}; overscans={OVERSCANS}"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/layered_assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
