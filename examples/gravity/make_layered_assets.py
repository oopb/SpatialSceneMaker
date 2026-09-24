from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

W, H = 1290, 2796

# Nine visible recessed stages: eight rounded-rectangle rings plus a center disc.
COLORS = [
    (17, 84, 73, 255),
    (23, 103, 87, 255),
    (30, 123, 101, 255),
    (39, 145, 117, 255),
    (50, 166, 133, 255),
    (64, 187, 150, 255),
    (82, 205, 167, 255),
    (105, 220, 184, 255),
    (145, 234, 207, 255),
]

BOXES = [
    (70, 680, W - 70, 2250, 170),
    (105, 735, W - 105, 2195, 160),
    (145, 800, W - 145, 2130, 148),
    (190, 875, W - 190, 2055, 135),
    (240, 960, W - 240, 1970, 121),
    (300, 1055, W - 300, 1875, 106),
    (370, 1160, W - 370, 1770, 91),
    (445, 1275, W - 445, 1655, 72),
]
CENTER = (W // 2, 1465, 135)

# Every layer image is intentionally larger than the screen. The builder uses
# matching quad overscan so the artwork lines up at rest but still has hidden
# pixels around the viewport during motion.
OVERSCANS = [1.04, 1.055, 1.075, 1.10, 1.13, 1.165, 1.205, 1.25, 1.31]
BACKGROUND_OVERSCAN = 1.38


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
        c = (7 + int(4 * t), 49 + int(9 * t), 43 + int(7 * t), 255)
        draw.line((0, y, cw, y), fill=c)

    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = ox + W // 2, oy + 1465
    gd.ellipse((cx - 470, cy - 470, cx + 470, cy + 470), fill=(105, 255, 226, 16))
    glow = glow.filter(ImageFilter.GaussianBlur(145))
    return Image.alpha_composite(canvas, glow)


def ring_slice(outer_box, inner_shape, color, scale: float) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)
    alpha = Image.new("L", canvas.size, 0)
    ad = ImageDraw.Draw(alpha)

    x0, y0, x1, y1, radius = outer_box
    ad.rounded_rectangle(
        (ox + x0, oy + y0, ox + x1, oy + y1),
        radius=radius,
        fill=255,
    )

    if inner_shape[0] == "rounded":
        _, ix0, iy0, ix1, iy1, ir = inner_shape
        ad.rounded_rectangle(
            (ox + ix0, oy + iy0, ox + ix1, oy + iy1),
            radius=ir,
            fill=0,
        )
    else:
        _, cx, cy, rr = inner_shape
        ad.ellipse(
            (ox + cx - rr, oy + cy - rr, ox + cx + rr, oy + cy + rr),
            fill=0,
        )

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(alpha)
    return layer


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
    hd.ellipse((cx - 100, cy - 100, cx + 100, cy + 100), fill=(255, 255, 255, 34))
    highlight = highlight.filter(ImageFilter.GaussianBlur(30))

    # Keep the glow clipped inside the center disc.
    clipped_alpha = Image.composite(
        highlight.getchannel("A"),
        Image.new("L", canvas.size, 0),
        alpha,
    )
    highlight.putalpha(clipped_alpha)
    return Image.alpha_composite(layer, highlight)


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    make_background().save(out_dir / "background.png")

    for i, outer in enumerate(BOXES):
        if i + 1 < len(BOXES):
            inner = ("rounded",) + BOXES[i + 1]
        else:
            inner = ("circle",) + CENTER
        ring_slice(outer, inner, COLORS[i], OVERSCANS[i]).save(out_dir / f"slice_{i:02d}.png")

    center_circle(COLORS[-1], OVERSCANS[-1]).save(out_dir / f"slice_{len(BOXES):02d}.png")
    print(f"Generated {len(BOXES) + 1} slices + background in {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/layered_assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
