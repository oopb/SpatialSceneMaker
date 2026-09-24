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

# Restore the opening sizes from the earlier six-stage version.
# These were the INNER contours of the old ring-based artwork, so using them as
# holes keeps the familiar proportions while every layer itself is now full-screen.
ROUNDED_HOLES = [
    (135, 790, W - 135, 2140, 150),
    (210, 900, W - 210, 2030, 130),
    (300, 1030, W - 300, 1900, 108),
    (405, 1180, W - 405, 1750, 82),
]
CENTER = (W // 2, 1465, 165)

# The logical artwork on every layer is full-screen. The expanded canvases below
# only provide hidden pixels outside the viewport for parallax safety.
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
    # Fully opaque across the entire oversized canvas. At rest this presents a
    # screen-sized plate; the extra area is only hidden overscan.
    return Image.new("L", size, 255)


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
    gd.ellipse((cx - 420, cy - 420, cx + 420, cy + 420), fill=(100, 245, 222, 10))
    glow = glow.filter(ImageFilter.GaussianBlur(150))
    return Image.alpha_composite(canvas, glow)


def _soft_hole_highlight(hole: Image.Image, surface_alpha: Image.Image) -> Image.Image:
    # Build a two-scale highlight. The broad component starts the transition
    # gently; the narrow component increases brightness smoothly as it approaches
    # the cut-out edge. There is no dark shadow component.
    broad = hole.filter(ImageFilter.GaussianBlur(58)).point(
        lambda p: min(18, int(p * 0.07))
    )
    near = hole.filter(ImageFilter.GaussianBlur(17)).point(
        lambda p: min(42, int(p * 0.17))
    )
    alpha = ImageChops.add(broad, near)
    alpha = ImageChops.multiply(alpha, surface_alpha)

    highlight = Image.new("RGBA", hole.size, (228, 255, 248, 255))
    highlight.putalpha(alpha)
    return highlight


def plate_slice(hole_shape, color, scale: float) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)

    surface_alpha = _full_surface_alpha(canvas.size)
    hole = _shape_mask(canvas.size, ox, oy, hole_shape)
    visible_alpha = ImageChops.subtract(surface_alpha, hole)

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(visible_alpha)

    # Soft highlight increment toward the cut-out edge.
    # Mask with visible_alpha so no highlight leaks into the transparent hole.
    highlight = _soft_hole_highlight(hole, visible_alpha)
    layer = Image.alpha_composite(layer, highlight)

    # Extremely subtle global lift keeps the large plate from appearing as a
    # perfectly flat block while preserving the no-shadow design.
    face = Image.new("RGBA", canvas.size, (255, 255, 255, 4))
    face.putalpha(visible_alpha.point(lambda p: 4 if p else 0))
    return Image.alpha_composite(layer, face)


def bottom_surface(color, scale: float) -> Image.Image:
    # The bottom-most "circle" is also a full-screen image. Its circular shape in
    # the final composition comes solely from the circular hole in the plate above.
    canvas, ox, oy = _expanded_canvas(scale)
    layer = Image.new("RGBA", canvas.size, color)

    cx, cy, _ = CENTER
    cx += ox
    cy += oy

    # Broad, natural center lift extending far beyond the visible circular hole,
    # so the gradient remains continuous when this deepest layer moves the most.
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

    # Four full-screen plates with the restored rounded-rectangle openings.
    for i, hole in enumerate(ROUNDED_HOLES):
        plate_slice(
            ("rounded",) + hole,
            COLORS[i],
            OVERSCANS[i],
        ).save(out_dir / f"slice_{i:02d}.png")

    # Fifth full-screen plate with the restored circular opening.
    plate_slice(
        ("circle",) + CENTER,
        COLORS[len(ROUNDED_HOLES)],
        OVERSCANS[len(ROUNDED_HOLES)],
    ).save(out_dir / f"slice_{len(ROUNDED_HOLES):02d}.png")

    # Sixth/deepest layer is also a full-screen image.
    bottom_surface(COLORS[-1], OVERSCANS[-1]).save(
        out_dir / f"slice_{len(ROUNDED_HOLES) + 1:02d}.png"
    )

    print(
        f"Generated {len(ROUNDED_HOLES) + 2} full-screen slices + background in {out_dir}"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/layered_assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
