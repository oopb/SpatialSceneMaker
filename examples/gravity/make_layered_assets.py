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

# Logical artwork is full-screen. Extra canvas is hidden parallax safety margin.
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


def _inset_highlight(
    reveal_shape,
    size,
    ox: int,
    oy: int,
    visible_alpha: Image.Image,
) -> Image.Image:
    # The highlight belongs to the LOWER surface revealed through the opening
    # above it. This is the key recessed cue: brightness is strongest just
    # INSIDE the parent opening and fades naturally toward the center.
    reveal = _shape_mask(size, ox, oy, reveal_shape)

    # Inside-edge bands. For a binary mask M, M - blur(M) is positive only on
    # the inside of the boundary. Two blur radii create a smooth long falloff
    # plus a gentle near-edge lift instead of a hard glowing ring.
    broad_blur = reveal.filter(ImageFilter.GaussianBlur(92))
    near_blur = reveal.filter(ImageFilter.GaussianBlur(30))

    broad = ImageChops.subtract(reveal, broad_blur).point(
        lambda p: min(22, int(p * 0.11))
    )
    near = ImageChops.subtract(reveal, near_blur).point(
        lambda p: min(34, int(p * 0.17))
    )

    alpha = ImageChops.add(broad, near)
    alpha = ImageChops.multiply(alpha, visible_alpha)

    highlight = Image.new("RGBA", size, (232, 255, 249, 255))
    highlight.putalpha(alpha)
    return highlight


def plate_slice(
    hole_shape,
    color,
    scale: float,
    *,
    reveal_shape=None,
) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)

    surface_alpha = _full_surface_alpha(canvas.size)
    hole = _shape_mask(canvas.size, ox, oy, hole_shape)
    visible_alpha = ImageChops.subtract(surface_alpha, hole)

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(visible_alpha)

    # Do NOT brighten this plate around its own hole. That made the hole edge
    # look raised/convex. Instead, brighten this plate only where it is exposed
    # through the opening of the plate above.
    if reveal_shape is not None:
        layer = Image.alpha_composite(
            layer,
            _inset_highlight(
                reveal_shape,
                canvas.size,
                ox,
                oy,
                visible_alpha,
            ),
        )

    return layer


def bottom_surface(
    color,
    scale: float,
    *,
    reveal_shape,
) -> Image.Image:
    # Bottom is also a full-screen image. The circular appearance comes only
    # from the hole in the plate above it.
    canvas, ox, oy = _expanded_canvas(scale)
    visible_alpha = _full_surface_alpha(canvas.size)

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(visible_alpha)

    # Same recessed lighting rule: the deepest image is softly brighter just
    # inside the circular opening through which it is viewed.
    return Image.alpha_composite(
        layer,
        _inset_highlight(
            reveal_shape,
            canvas.size,
            ox,
            oy,
            visible_alpha,
        ),
    )


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for old in out_dir.glob("slice_*.png"):
        old.unlink()

    make_background().save(out_dir / "background.png")

    rounded_shapes = [("rounded",) + hole for hole in ROUNDED_HOLES]
    circle_shape = ("circle",) + CENTER

    # Top plate: no inset highlight because no plate above reveals it.
    plate_slice(
        rounded_shapes[0],
        COLORS[0],
        OVERSCANS[0],
    ).save(out_dir / "slice_00.png")

    # Each lower plate is highlighted along the INSIDE boundary of the opening
    # through which the previous plate reveals it.
    for i in range(1, len(rounded_shapes)):
        plate_slice(
            rounded_shapes[i],
            COLORS[i],
            OVERSCANS[i],
            reveal_shape=rounded_shapes[i - 1],
        ).save(out_dir / f"slice_{i:02d}.png")

    # Fifth plate is revealed through the smallest rounded opening and itself
    # contains the final circular opening.
    plate_slice(
        circle_shape,
        COLORS[len(rounded_shapes)],
        OVERSCANS[len(rounded_shapes)],
        reveal_shape=rounded_shapes[-1],
    ).save(out_dir / f"slice_{len(rounded_shapes):02d}.png")

    # Deepest image is full-screen and revealed through the circle.
    bottom_surface(
        COLORS[-1],
        OVERSCANS[-1],
        reveal_shape=circle_shape,
    ).save(out_dir / f"slice_{len(rounded_shapes) + 1:02d}.png")

    print(
        f"Generated {len(rounded_shapes) + 2} full-screen slices + background in {out_dir}"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/layered_assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
