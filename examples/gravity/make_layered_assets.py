from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

from make_assets import H, LEVELS, W

# Rebuild the layered demo directly from make_assets.py instead of maintaining
# a second, independently tuned set of proportions.
#
# make_assets.py contains:
#   background + five rounded rectangles + one center circle
# so the layered version uses exactly seven main slices.
BACKGROUND_RGB = (7, 48, 43)
CENTER = (W // 2, 1455, 205)
CENTER_RGB = (137, 231, 207)

# Same discrete depth-map values as make_assets.py:
# background, five LEVELS, center circle.
DEPTH_GRAYS = [
    255,
    *[gray for _, _, _, _, _, gray in LEVELS],
    45,
]

# Keep the early layered implementation's progressively larger hidden border.
# There are seven entries because the geometry now matches make_assets.py's
# seven visible depth regions exactly.
OVERSCANS = [1.04, 1.055, 1.075, 1.10, 1.13, 1.165, 1.205]
BACKGROUND_OVERSCAN = 1.25


def _expanded_canvas(scale: float) -> tuple[Image.Image, int, int]:
    cw = int(math.ceil(W * scale))
    ch = int(math.ceil(H * scale))
    ox = (cw - W) // 2
    oy = (ch - H) // 2
    return Image.new("RGBA", (cw, ch), (0, 0, 0, 0)), ox, oy


def _rounded_box(level) -> tuple[int, int, int, int, int]:
    margin_x, top, bottom, radius, _, _ = level
    return margin_x, top, W - margin_x, bottom, radius


def _draw_rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int, int],
    *,
    ox: int,
    oy: int,
    fill: int,
) -> None:
    x0, y0, x1, y1, radius = box
    draw.rounded_rectangle(
        (ox + x0, oy + y0, ox + x1, oy + y1),
        radius=radius,
        fill=fill,
    )


def background_slice(scale: float) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    draw = ImageDraw.Draw(canvas)
    cw, ch = canvas.size

    # Match the subtle vertical shading in make_assets.py.
    for y in range(ch):
        t = min(1.0, max(0.0, (y - oy) / max(H - 1, 1)))
        color = (
            BACKGROUND_RGB[0] + int(3 * t),
            BACKGROUND_RGB[1] + int(7 * t),
            BACKGROUND_RGB[2] + int(5 * t),
            255,
        )
        draw.line((0, y, cw, y), fill=color)

    # The next layer occupies LEVELS[0]; cut that region out of the background
    # slice so all seven slices reproduce the same nested composition.
    alpha = Image.new("L", canvas.size, 255)
    ad = ImageDraw.Draw(alpha)
    _draw_rounded(
        ad,
        _rounded_box(LEVELS[0]),
        ox=ox,
        oy=oy,
        fill=0,
    )
    canvas.putalpha(alpha)
    return canvas


def rounded_ring_slice(
    level_index: int,
    scale: float,
) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    alpha = Image.new("L", canvas.size, 0)
    ad = ImageDraw.Draw(alpha)

    outer = _rounded_box(LEVELS[level_index])
    _draw_rounded(ad, outer, ox=ox, oy=oy, fill=255)

    if level_index + 1 < len(LEVELS):
        inner = _rounded_box(LEVELS[level_index + 1])
        _draw_rounded(ad, inner, ox=ox, oy=oy, fill=0)
    else:
        cx, cy, radius = CENTER
        ad.ellipse(
            (
                ox + cx - radius,
                oy + cy - radius,
                ox + cx + radius,
                oy + cy + radius,
            ),
            fill=0,
        )

    color = LEVELS[level_index][4] + (255,)
    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(alpha)
    return layer


def center_circle_slice(scale: float) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    alpha = Image.new("L", canvas.size, 0)
    ad = ImageDraw.Draw(alpha)

    cx, cy, radius = CENTER
    ad.ellipse(
        (
            ox + cx - radius,
            oy + cy - radius,
            ox + cx + radius,
            oy + cy + radius,
        ),
        fill=255,
    )

    layer = Image.new("RGBA", canvas.size, CENTER_RGB + (255,))
    layer.putalpha(alpha)
    return layer


def make_backfill(scale: float = BACKGROUND_OVERSCAN) -> Image.Image:
    # Backfill is only a safety surface for motion gaps. Keep it visually
    # consistent with the make_assets.py background without extra glow.
    canvas, ox, oy = _expanded_canvas(scale)
    draw = ImageDraw.Draw(canvas)
    cw, ch = canvas.size
    for y in range(ch):
        t = min(1.0, max(0.0, (y - oy) / max(H - 1, 1)))
        color = (
            BACKGROUND_RGB[0] + int(3 * t),
            BACKGROUND_RGB[1] + int(7 * t),
            BACKGROUND_RGB[2] + int(5 * t),
            255,
        )
        draw.line((0, y, cw, y), fill=color)
    return canvas


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for old in out_dir.glob("slice_*.png"):
        old.unlink()

    make_backfill().save(out_dir / "background.png")

    # Slice 0: outer background region.
    background_slice(OVERSCANS[0]).save(out_dir / "slice_00.png")

    # Slices 1..5: exactly the five rounded regions from make_assets.py.
    for level_index in range(len(LEVELS)):
        rounded_ring_slice(
            level_index,
            OVERSCANS[level_index + 1],
        ).save(out_dir / f"slice_{level_index + 1:02d}.png")

    # Slice 6: exact center circle from make_assets.py.
    center_circle_slice(OVERSCANS[-1]).save(
        out_dir / f"slice_{len(LEVELS) + 1:02d}.png"
    )

    print(
        f"Generated {len(DEPTH_GRAYS)} main slices + background in {out_dir}"
    )
    print(f"source LEVELS: {LEVELS}")
    print(f"center: {CENTER}")
    print(f"depth grays: {DEPTH_GRAYS}")
    print(f"overscans: {OVERSCANS}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/layered_assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
