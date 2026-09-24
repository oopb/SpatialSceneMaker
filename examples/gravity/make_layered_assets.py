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
COLORS = [
    (18, 86, 75, 255),
    (24, 101, 86, 255),
    (31, 119, 99, 255),
    (40, 139, 114, 255),
    (52, 161, 130, 255),
    (67, 184, 148, 255),
    (91, 207, 171, 255),
    (137, 229, 204, 255),
]

# Preserve the original outer rounded opening and the original innermost
# rounded-opening width, but insert two extra rounded layers between them.
# Every rounded opening is a uniform scale of the same base shape, so width,
# height, corner radius and perimeter all scale by the same ratio.
BASE_HOLE_WIDTH = 1020
BASE_HOLE_HEIGHT = 1350
BASE_HOLE_RADIUS = 150
ROUNDED_HOLE_COUNT = 6
INNER_ROUNDED_WIDTH = 480
HOLE_SCALE_RATIO = (
    INNER_ROUNDED_WIDTH / BASE_HOLE_WIDTH
) ** (1.0 / (ROUNDED_HOLE_COUNT - 1))


def _scaled_hole(scale: float) -> tuple[int, int, int, int, int]:
    width = round(BASE_HOLE_WIDTH * scale)
    height = round(BASE_HOLE_HEIGHT * scale)
    radius = round(BASE_HOLE_RADIUS * scale)

    x0 = round(CENTER_X - width / 2)
    y0 = round(CENTER_Y - height / 2)
    return x0, y0, x0 + width, y0 + height, radius


HOLE_SCALES = [
    HOLE_SCALE_RATIO**i
    for i in range(ROUNDED_HOLE_COUNT)
]
ROUNDED_HOLES = [
    _scaled_hole(scale)
    for scale in HOLE_SCALES
]

# Keep the terminal circular opening from the earlier design.
CENTER = (CENTER_X, CENTER_Y, 165)

# Progressive hidden border for the eight slices. Upper layers keep little
# overscan for sharpness; deeper layers get more room for parallax.
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
        c = (7 + int(4 * t), 48 + int(8 * t), 42 + int(6 * t), 255)
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
    print(f"rounded-hole scales: {HOLE_SCALES}")
    print(f"rounded holes: {ROUNDED_HOLES}")
    print(f"circle: {CENTER}")
    print(f"overscans: {OVERSCANS}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/layered_assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
