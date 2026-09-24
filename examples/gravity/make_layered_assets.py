from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

W, H = 1290, 2796
CENTER_X = W // 2
CENTER_Y = 1465

# Eight visible stages:
# six full-screen rounded-cutout plates,
# one full-screen circular-cutout plate,
# one full-screen bottom image.
#
# Increase color separation between adjacent stages so the depth stack remains
# visually readable even without highlight/glow overlays.
COLORS = [
    (10, 58, 51, 255),
    (18, 82, 70, 255),
    (28, 108, 90, 255),
    (40, 136, 110, 255),
    (56, 166, 132, 255),
    (76, 196, 154, 255),
    (104, 220, 180, 255),
    (154, 240, 214, 255),
]

# Shrink the innermost rounded opening further while preserving strict
# geometric similarity across all six rounded openings.
ROUNDED_HOLE_COUNT = 6
INNER_ROUNDED_WIDTH = 300
INNER_ROUNDED_HEIGHT = 356
INNER_ROUNDED_RADIUS = 51
OUTER_ROUNDED_WIDTH = 1020

TOTAL_ROUNDED_SCALE = OUTER_ROUNDED_WIDTH / INNER_ROUNDED_WIDTH
HOLE_SCALE_RATIO = TOTAL_ROUNDED_SCALE ** (1.0 / (ROUNDED_HOLE_COUNT - 1))


def _scaled_hole_from_inner(scale: float) -> tuple[int, int, int, int, int]:
    width = round(INNER_ROUNDED_WIDTH * scale)
    height = round(INNER_ROUNDED_HEIGHT * scale)
    radius = round(INNER_ROUNDED_RADIUS * scale)

    x0 = round(CENTER_X - width / 2)
    y0 = round(CENTER_Y - height / 2)
    return x0, y0, x0 + width, y0 + height, radius


# Outer -> inner.
HOLE_SCALES = [
    HOLE_SCALE_RATIO ** i
    for i in reversed(range(ROUNDED_HOLE_COUNT))
]
ROUNDED_HOLES = [
    _scaled_hole_from_inner(scale)
    for scale in HOLE_SCALES
]

# Shrink the central circle to roughly half of the previous radius.
CENTER = (CENTER_X, CENTER_Y, 82)

# Progressive hidden border for the eight slices. Upper layers retain more
# effective texture resolution; deeper layers keep extra margin for parallax.
OVERSCANS = [1.035, 1.048, 1.062, 1.082, 1.105, 1.135, 1.18, 1.24]
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
        (
            ox + cx - radius,
            oy + cy - radius,
            ox + cx + radius,
            oy + cy + radius,
        ),
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
        c = (5 + int(4 * t), 39 + int(7 * t), 34 + int(6 * t), 255)
        draw.line((0, y, cw, y), fill=c)

    return canvas


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
    return layer


def bottom_surface(
    color,
    scale: float,
) -> Image.Image:
    canvas, _, _ = _expanded_canvas(scale)
    return Image.new("RGBA", canvas.size, color)


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for old in out_dir.glob("slice_*.png"):
        old.unlink()

    make_background().save(out_dir / "background.png")

    rounded_shapes = [
        ("rounded",) + hole
        for hole in ROUNDED_HOLES
    ]
    circle_shape = ("circle",) + CENTER

    for i, shape in enumerate(rounded_shapes):
        plate_slice(
            shape,
            COLORS[i],
            OVERSCANS[i],
        ).save(out_dir / f"slice_{i:02d}.png")

    circle_index = len(rounded_shapes)
    plate_slice(
        circle_shape,
        COLORS[circle_index],
        OVERSCANS[circle_index],
    ).save(out_dir / f"slice_{circle_index:02d}.png")

    bottom_index = circle_index + 1
    bottom_surface(
        COLORS[bottom_index],
        OVERSCANS[bottom_index],
    ).save(out_dir / f"slice_{bottom_index:02d}.png")

    print(
        f"Generated {bottom_index + 1} full-screen slices + background "
        f"in {out_dir}"
    )
    print(f"rounded-hole scale ratio: {HOLE_SCALE_RATIO}")
    print(f"rounded-hole scales outer -> inner: {HOLE_SCALES}")
    print(f"rounded holes outer -> inner: {ROUNDED_HOLES}")
    print(f"circle: {CENTER}")
    print(f"overscans: {OVERSCANS}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/layered_assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
