from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from make_assets import H, LEVELS, W

# The layered demo follows make_assets.py for proportions/colors, but every
# main slice is a FULL-SCREEN plate. Each plate reveals the next deeper stage
# only through a rounded-rectangle or circular cut-out.
#
# Seven main slices:
#   0 background plate -> hole = LEVELS[0]
#   1 LEVELS[0] plate -> hole = LEVELS[1]
#   2 LEVELS[1] plate -> hole = LEVELS[2]
#   3 LEVELS[2] plate -> hole = LEVELS[3]
#   4 LEVELS[3] plate -> hole = LEVELS[4]
#   5 LEVELS[4] plate -> hole = center circle
#   6 center-color bottom plate -> no hole
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

# Keep progressively larger hidden margins for deeper plates.
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


def _rounded_mask(
    size,
    ox: int,
    oy: int,
    box: tuple[int, int, int, int, int],
) -> Image.Image:
    x0, y0, x1, y1, radius = box
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (ox + x0, oy + y0, ox + x1, oy + y1),
        radius=radius,
        fill=255,
    )
    return mask


def _circle_mask(size, ox: int, oy: int) -> Image.Image:
    cx, cy, radius = CENTER
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse(
        (
            ox + cx - radius,
            oy + cy - radius,
            ox + cx + radius,
            oy + cy + radius,
        ),
        fill=255,
    )
    return mask


def _full_alpha(size) -> Image.Image:
    return Image.new("L", size, 255)


def _background_rgba(scale: float) -> tuple[Image.Image, int, int]:
    canvas, ox, oy = _expanded_canvas(scale)
    draw = ImageDraw.Draw(canvas)
    cw, ch = canvas.size

    # Match make_assets.py's subtle vertical background shading.
    for y in range(ch):
        t = min(1.0, max(0.0, (y - oy) / max(H - 1, 1)))
        color = (
            BACKGROUND_RGB[0] + int(3 * t),
            BACKGROUND_RGB[1] + int(7 * t),
            BACKGROUND_RGB[2] + int(5 * t),
            255,
        )
        draw.line((0, y, cw, y), fill=color)

    return canvas, ox, oy


def background_plate(scale: float) -> Image.Image:
    canvas, ox, oy = _background_rgba(scale)
    hole = _rounded_mask(
        canvas.size,
        ox,
        oy,
        _rounded_box(LEVELS[0]),
    )
    visible = ImageChops.subtract(_full_alpha(canvas.size), hole)
    canvas.putalpha(visible)
    return canvas


def color_plate(
    color: tuple[int, int, int],
    scale: float,
    *,
    rounded_hole: tuple[int, int, int, int, int] | None = None,
    circle_hole: bool = False,
) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    layer = Image.new("RGBA", canvas.size, color + (255,))

    if rounded_hole is not None:
        hole = _rounded_mask(canvas.size, ox, oy, rounded_hole)
        visible = ImageChops.subtract(_full_alpha(canvas.size), hole)
        layer.putalpha(visible)
    elif circle_hole:
        hole = _circle_mask(canvas.size, ox, oy)
        visible = ImageChops.subtract(_full_alpha(canvas.size), hole)
        layer.putalpha(visible)

    return layer


def make_backfill(scale: float = BACKGROUND_OVERSCAN) -> Image.Image:
    canvas, _, _ = _background_rgba(scale)
    return canvas


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for old in out_dir.glob("slice_*.png"):
        old.unlink()

    make_backfill().save(out_dir / "background.png")

    # 0: full-screen background with the outermost rounded hole.
    background_plate(OVERSCANS[0]).save(out_dir / "slice_00.png")

    # 1..4: full-screen colored plates, each cut by the NEXT rounded hole.
    for level_index in range(len(LEVELS) - 1):
        color_plate(
            LEVELS[level_index][4],
            OVERSCANS[level_index + 1],
            rounded_hole=_rounded_box(LEVELS[level_index + 1]),
        ).save(out_dir / f"slice_{level_index + 1:02d}.png")

    # 5: full-screen innermost rounded-region color with the center circle cut out.
    color_plate(
        LEVELS[-1][4],
        OVERSCANS[len(LEVELS)],
        circle_hole=True,
    ).save(out_dir / f"slice_{len(LEVELS):02d}.png")

    # 6: deepest layer is still a full-screen image. It only appears circular
    # because the layer above has a circular cut-out.
    color_plate(
        CENTER_RGB,
        OVERSCANS[len(LEVELS) + 1],
    ).save(out_dir / f"slice_{len(LEVELS) + 1:02d}.png")

    print(
        f"Generated {len(DEPTH_GRAYS)} full-screen cutout slices + background "
        f"in {out_dir}"
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
