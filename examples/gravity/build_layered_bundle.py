from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image

from spatialscene_maker.formats import write_ssmesh, write_sstexture
from spatialscene_maker.mesh import build_full_frame_quad, merge_meshes
from spatialscene_maker.project import build_v3_project, expanded_vertical_fov_rad
from spatialscene_maker.texture import encode_astc_4x4_srgb_pil

from make_layered_assets import (
    BACKGROUND_OVERSCAN,
    CENTER,
    H,
    OVERSCANS,
    ROUNDED_HOLES,
    W,
)

# Increase vertical separation between stages while keeping the deepest stage
# at the original near depth. Height above the bottom is strictly proportional
# to the perimeter of the opening for that stage.
OUTER_DEPTH = 75.0
INNER_DEPTH = 3.7

ROUNDED_PERIMETERS = [
    2.0 * ((x1 - x0) + (y1 - y0) - 4.0 * radius)
    + 2.0 * math.pi * radius
    for x0, y0, x1, y1, radius in ROUNDED_HOLES
]
CIRCLE_PERIMETER = 2.0 * math.pi * CENTER[2]

# Eight stages:
# six rounded-opening plates, one circular-opening plate, one bottom surface.
# The bottom surface has zero opening perimeter / zero relative height.
WINDOW_PERIMETERS = [
    *ROUNDED_PERIMETERS,
    CIRCLE_PERIMETER,
    0.0,
]

HEIGHT_PER_PERIMETER = (
    OUTER_DEPTH - INNER_DEPTH
) / WINDOW_PERIMETERS[0]

PARALLAX_DEPTHS = [
    INNER_DEPTH + perimeter * HEIGHT_PER_PERIMETER
    for perimeter in WINDOW_PERIMETERS
]

BACKFILL_PARALLAX_DEPTH = INNER_DEPTH * 0.85


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build the layered gravity SpatialScene bundle"
    )
    ap.add_argument(
        "asset_dir",
        nargs="?",
        default="examples/gravity/layered_assets",
    )
    ap.add_argument("-o", "--output", default="GravityLayered.spatialscene")
    ap.add_argument("--fov", type=float, default=45.0)
    ap.add_argument("--texture-size", type=int, default=3072)
    ap.add_argument("--astcenc")
    ap.add_argument(
        "--astc-quality",
        choices=(
            "fastest",
            "fast",
            "medium",
            "thorough",
            "verythorough",
            "exhaustive",
        ),
        default="thorough",
    )
    ap.add_argument("--scene-id")
    args = ap.parse_args()

    asset_dir = Path(args.asset_dir)
    slices = sorted(asset_dir.glob("slice_*.png"))
    if len(slices) != len(PARALLAX_DEPTHS):
        raise SystemExit(
            f"Expected {len(PARALLAX_DEPTHS)} slices, found {len(slices)} in "
            f"{asset_dir}. Run make_layered_assets.py again so stale slices "
            "are removed."
        )

    bg_path = asset_dir / "background.png"
    if not bg_path.exists():
        raise SystemExit(f"Missing {bg_path}")

    aspect = W / H

    meshes = []
    for idx in reversed(range(len(PARALLAX_DEPTHS))):
        meshes.append(
            build_full_frame_quad(
                PARALLAX_DEPTHS[idx],
                aspect,
                args.fov,
                texture_size=args.texture_size,
                texture_slice=idx,
                overscan=OVERSCANS[idx],
            )
        )
    main_vertices, main_indices = merge_meshes(meshes)

    backfill_fov_deg = math.degrees(
        expanded_vertical_fov_rad(args.fov, 1.16)
    )
    backfill_vertices, backfill_indices = build_full_frame_quad(
        BACKFILL_PARALLAX_DEPTH,
        aspect,
        backfill_fov_deg,
        texture_size=args.texture_size,
        texture_slice=0,
        overscan=BACKGROUND_OVERSCAN,
    )

    print(
        f"Encoding ASTC slices at {args.texture_size}x{args.texture_size}, "
        f"quality={args.astc_quality}..."
    )
    payloads = [
        encode_astc_4x4_srgb_pil(
            Image.open(path).convert("RGBA"),
            size=args.texture_size,
            executable=args.astcenc,
            quality=args.astc_quality,
        )
        for path in slices
    ]
    bg_payload = encode_astc_4x4_srgb_pil(
        Image.open(bg_path).convert("RGBA"),
        size=args.texture_size,
        executable=args.astcenc,
        quality=args.astc_quality,
    )

    out = Path(args.output)
    if out.suffix != ".spatialscene":
        out = out.with_suffix(".spatialscene")
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    write_ssmesh(
        assets / "main.ssmesh",
        main_vertices,
        main_indices,
    )
    write_ssmesh(
        assets / "backfill.ssmesh",
        backfill_vertices,
        backfill_indices,
    )
    write_sstexture(
        assets / "main.sstexture",
        payloads,
        args.texture_size,
        args.texture_size,
    )
    write_sstexture(
        assets / "backfill.sstexture",
        [bg_payload],
        args.texture_size,
        args.texture_size,
    )

    project = build_v3_project(
        W,
        H,
        args.fov,
        (min(PARALLAX_DEPTHS), max(PARALLAX_DEPTHS)),
        (
            BACKFILL_PARALLAX_DEPTH,
            BACKFILL_PARALLAX_DEPTH + 0.001,
        ),
        scene_id=args.scene_id,
    )
    project["generator"].update(
        {
            "name": "SpatialSceneMaker recessed gravity",
            "strategy": (
                "Eight full-screen texture slices; six geometrically similar "
                "rounded openings plus the preserved terminal circular opening; "
                "no highlight overlay; increased color/depth contrast; relative "
                "height proportional to opening perimeter; normal offset "
                "direction with strongly increased motion amplitude."
            ),
            "layerCount": len(PARALLAX_DEPTHS),
            "windowPerimetersOuterToInner": WINDOW_PERIMETERS,
            "parallaxDepthsOuterToInner": PARALLAX_DEPTHS,
            "layerOverscansOuterToInner": OVERSCANS,
            "backgroundOverscan": BACKGROUND_OVERSCAN,
            "compositingOrder": "inner-to-outer",
            "textureSize": args.texture_size,
            "astcQuality": args.astc_quality,
        }
    )

    # Restore the positive offset direction and substantially increase the
    # device-motion amplitude compared with the earlier 0.025 setting.
    project["camera"]["motionRange"] = 0.05
    project["camera"]["overscan"] = 0.018

    (out / "project.json").write_text(
        json.dumps(project, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Generated: {out}")
    print(f"main texture slices: {len(payloads)}")
    print(
        f"main mesh: {len(main_vertices)} vertices / "
        f"{len(main_indices) // 3} triangles"
    )
    print(f"window perimeters outer -> inner: {WINDOW_PERIMETERS}")
    print(f"parallax depths outer -> inner: {PARALLAX_DEPTHS}")
    print(f"overscans outer -> inner: {OVERSCANS}")
    print("camera motion direction: positive; amplitude doubled (motionRange=0.05)")
    print(
        f"texture: {args.texture_size}x{args.texture_size}, "
        f"ASTC quality={args.astc_quality}"
    )
    print("draw/compositing order: inner -> outer")


if __name__ == "__main__":
    main()
