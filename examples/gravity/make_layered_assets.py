from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H = 1290, 2796

# Five large cut-out plates plus one bottom disc.
# All plates occupy the same broad area; only their openings change. This makes
# every stage read as a surface that the next stage is recessed behind.
COLORS = [
    (18, 86, 75, 255),
    (27, 112, 94, 255),
    (39, 143, 117, 255),
    (56, 175, 141, 255),
    (82, 205, 169, 255),
    (137, 229, 204, 255),
]

# The shared large plate. It intentionally extends close to the sides of the
# screen; per-layer overscan supplies additional hidden pixels during motion.
PLATE = (58, 655, W - 58, 2275, 180)

# Cut-out openings, outer/top -> inner/bottom. Compared with the previous
# revision these openings are smaller, leaving visibly thicker plate edges.
HOLES = [
    (190, 820, W - 190, 2110, 145),
    (285, 940, W - 285, 1990, 125),
    (380, 1070, W - 380, 1860, 105),
    (470, 1200, W - 470, 1730, 82),
]
CENTER = (W // 2, 1465, 128)

# Upper stages move least; deeper stages have more hidden border because their
# apparent motion is larger.
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
    gd.ellipse((cx - 420, cy - 420, cx + 420, cy + 420), fill=(100, 245, 222, 12))
    glow = glow.filter(ImageFilter.GaussianBlur(145))
    return Image.alpha_composite(canvas, glow)


def plate_slice(hole_shape, color, scale: float) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    plate_alpha = _rounded_mask(canvas.size, ox, oy, PLATE)
    hole = _shape_mask(canvas.size, ox, oy, hole_shape)
    plate_alpha = ImageChops.subtract(plate_alpha, hole)

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(plate_alpha)

    # Recess cue: a soft, low-opacity highlight immediately outside the opening.
    # There is intentionally no dark shadow in this version.
    blurred_hole = hole.filter(ImageFilter.GaussianBlur(20))
    lip_alpha = ImageChops.multiply(blurred_hole, plate_alpha).point(
        lambda p: min(52, int(p * 0.30))
    )
    lip = Image.new("RGBA", canvas.size, (224, 255, 247, 255))
    lip.putalpha(lip_alpha)
    layer = Image.alpha_composite(layer, lip)

    # Extremely subtle broad face lift so the plate still feels soft rather than
    # like a flat vector cutout.
    face = Image.new("RGBA", canvas.size, (255, 255, 255, 5))
    face.putalpha(plate_alpha.point(lambda p: 5 if p else 0))
    return Image.alpha_composite(layer, face)


def center_disc(color, scale: float) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    alpha = _circle_mask(canvas.size, ox, oy, CENTER)

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(alpha)

    # Soft center lift, matching the bright-lip language without introducing a
    # directional shadow.
    cx, cy, radius = CENTER
    cx += ox
    cy += oy
    highlight = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.ellipse(
        (cx - radius + 26, cy - radius + 26, cx + radius - 26, cy + radius - 26),
        fill=(255, 255, 255, 20),
    )
    highlight = highlight.filter(ImageFilter.GaussianBlur(30))
    highlight.putalpha(
        Image.composite(
            highlight.getchannel("A"),
            Image.new("L", canvas.size, 0),
            alpha,
        )
    )
    return Image.alpha_composite(layer, highlight)


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("slice_*.png"):
        old.unlink()

    make_background().save(out_dir / "background.png")

    for i, hole in enumerate(HOLES):
        plate_slice(
            ("rounded",) + hole,
            COLORS[i],
            OVERSCANS[i],
        ).save(out_dir / f"slice_{i:02d}.png")

    # The fifth plate opens into the bottom-most circular stage.
    plate_slice(
        ("circle",) + CENTER,
        COLORS[len(HOLES)],
        OVERSCANS[len(HOLES)],
    ).save(out_dir / f"slice_{len(HOLES):02d}.png")

    center_disc(COLORS[-1], OVERSCANS[-1]).save(
        out_dir / f"slice_{len(HOLES) + 1:02d}.png"
    )
    print(f"Generated {len(HOLES) + 2} slices + background in {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/layered_assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
