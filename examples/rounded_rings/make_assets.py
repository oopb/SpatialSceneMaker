from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1290, 2796
CENTER_X = W // 2
CENTER_Y = H // 2

# Six rounded-rectangle rings, top -> bottom.
#
# The rings are concentric, and every upper ring's OUTER rounded rectangle is
# strictly contained inside the next lower ring's OUTER rounded rectangle.
# The openings are deliberately much smaller than the outer shapes so the
# visible bands are thick instead of thin outlines.
#
# (outer_width, outer_height, outer_radius,
#  inner_width, inner_height, inner_radius,
#  RGBA color)
RINGS = [
    (360, 560, 90, 120, 190, 38, (126, 226, 198, 255)),
    (520, 820, 125, 180, 290, 52, (96, 194, 169, 255)),
    (700, 1120, 165, 250, 400, 70, (70, 160, 142, 255)),
    (880, 1460, 205, 320, 530, 88, (48, 127, 115, 255)),
    (1040, 1830, 245, 390, 680, 106, (31, 96, 89, 255)),
    (1190, 2280, 285, 470, 860, 130, (19, 68, 64, 255)),
]

# Deepest layer: full-screen fill, darker than every rounded ring.
BOTTOM_COLOR = (8, 40, 38, 255)

# Upper layers move more, so give them larger hidden texture margins.
# The final value belongs to the full-screen bottom layer.
OVERSCANS = [1.24, 1.20, 1.17, 1.14, 1.11, 1.08, 1.05]
BACKGROUND_OVERSCAN = 1.16


def _expanded_canvas(scale: float) -> tuple[Image.Image, int, int]:
    cw = int(math.ceil(W * scale))
    ch = int(math.ceil(H * scale))
    ox = (cw - W) // 2
    oy = (ch - H) // 2
    return Image.new("RGBA", (cw, ch), (0, 0, 0, 0)), ox, oy


def _centered_box(
    width: int,
    height: int,
    *,
    ox: int,
    oy: int,
) -> tuple[int, int, int, int]:
    x0 = ox + CENTER_X - width // 2
    y0 = oy + CENTER_Y - height // 2
    return x0, y0, x0 + width, y0 + height


def rounded_ring(
    outer_width: int,
    outer_height: int,
    outer_radius: int,
    inner_width: int,
    inner_height: int,
    inner_radius: int,
    color: tuple[int, int, int, int],
    scale: float,
) -> Image.Image:
    canvas, ox, oy = _expanded_canvas(scale)

    alpha = Image.new("L", canvas.size, 0)
    draw = ImageDraw.Draw(alpha)

    draw.rounded_rectangle(
        _centered_box(outer_width, outer_height, ox=ox, oy=oy),
        radius=outer_radius,
        fill=255,
    )
    draw.rounded_rectangle(
        _centered_box(inner_width, inner_height, ox=ox, oy=oy),
        radius=inner_radius,
        fill=0,
    )

    layer = Image.new("RGBA", canvas.size, color)
    layer.putalpha(alpha)
    return layer


def bottom_surface(
    color: tuple[int, int, int, int],
    scale: float,
) -> Image.Image:
    canvas, _, _ = _expanded_canvas(scale)
    return Image.new("RGBA", canvas.size, color)


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Guard the intended visual hierarchy: each deeper ring must fully contain
    # the previous ring in both screen axes, and every cut-out must remain
    # substantially smaller than its own outer rounded rectangle.
    for index, ring in enumerate(RINGS):
        ow, oh, _, iw, ih, _, _ = ring
        if not (iw < ow * 0.5 and ih < oh * 0.5):
            raise ValueError(
                f"Ring {index} opening is too large: outer={ow}x{oh}, "
                f"inner={iw}x{ih}"
            )
        if index:
            prev_ow, prev_oh = RINGS[index - 1][0], RINGS[index - 1][1]
            if not (prev_ow < ow and prev_oh < oh):
                raise ValueError(
                    f"Ring {index - 1} must fit fully inside ring {index}"
                )

    for old in out_dir.glob("slice_*.png"):
        old.unlink()

    # Backfill is only a safety surface for motion gaps.
    bottom_surface(BOTTOM_COLOR, BACKGROUND_OVERSCAN).save(
        out_dir / "background.png"
    )

    for index, spec in enumerate(RINGS):
        rounded_ring(*spec, OVERSCANS[index]).save(
            out_dir / f"slice_{index:02d}.png"
        )

    bottom_index = len(RINGS)
    bottom_surface(
        BOTTOM_COLOR,
        OVERSCANS[bottom_index],
    ).save(out_dir / f"slice_{bottom_index:02d}.png")

    print(
        f"Generated {len(RINGS)} rounded-ring slices + 1 full-screen bottom "
        f"layer in {out_dir}"
    )
    print(f"rings top -> bottom: {RINGS}")
    print(f"overscans top -> bottom: {OVERSCANS}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/rounded_rings/assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
