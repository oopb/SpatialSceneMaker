from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1290, 2796
CENTER_X = W // 2
CENTER_Y = H // 2

# Six concentric rounded-rectangle rings, top -> bottom.
#
# This is true ring-within-ring nesting:
# - OUTER rounded rectangles grow larger toward the bottom with a compact,
#   approximately constant 1.18x scale between adjacent layers.
# - INNER rounded rectangles stay on the established shrinking sequence.
#
# Therefore the complete visible band of ring N is contained inside the
# visible band of ring N+1: the lower ring extends farther outward while its
# hole retreats farther inward.
#
# (outer_width, outer_height, outer_radius,
#  inner_width, inner_height, inner_radius,
#  RGBA color)
RINGS = [
    (390, 607, 98, 240, 380, 58, (126, 226, 198, 255)),
    (460, 716, 115, 200, 315, 48, (96, 194, 169, 255)),
    (543, 845, 136, 165, 255, 39, (70, 160, 142, 255)),
    (641, 997, 160, 130, 200, 31, (48, 127, 115, 255)),
    (756, 1176, 189, 100, 150, 24, (31, 96, 89, 255)),
    (892, 1388, 223, 70, 105, 17, (19, 68, 64, 255)),
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

    # Validate true ring-within-ring nesting:
    # outer bounds must grow while holes must shrink. For concentric rings,
    # these two conditions make every upper visible ring lie inside the next
    # lower visible ring.
    for index, ring in enumerate(RINGS):
        ow, oh, outer_r, iw, ih, inner_r, _ = ring
        if not (iw < ow and ih < oh):
            raise ValueError(
                f"Ring {index} has invalid geometry: outer={ow}x{oh}, "
                f"inner={iw}x{ih}"
            )
        if not (0 < inner_r < outer_r):
            raise ValueError(
                f"Ring {index} radii must satisfy 0 < inner < outer"
            )

        if index:
            prev = RINGS[index - 1]
            prev_ow, prev_oh, prev_outer_r = prev[0], prev[1], prev[2]
            prev_iw, prev_ih, prev_inner_r = prev[3], prev[4], prev[5]

            if not (
                prev_ow < ow
                and prev_oh < oh
                and prev_outer_r < outer_r
            ):
                raise ValueError(
                    f"Ring {index} outer rounded rectangle must fully grow "
                    f"beyond ring {index - 1}"
                )

            if not (
                iw < prev_iw
                and ih < prev_ih
                and inner_r < prev_inner_r
            ):
                raise ValueError(
                    f"Ring {index} opening must shrink inside ring {index - 1}"
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
