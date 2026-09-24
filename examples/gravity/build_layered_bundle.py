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

from make_layered_assets import BACKGROUND_OVERSCAN, OVERSCANS

# Requested motion profile:
# top/outer stage moves the least; each lower/inner stage moves more.
# Larger camera-space depth produces less apparent translation, so values
# decrease monotonically toward the center.
PARALLAX_DEPTHS = [
    55.0,
    28.0,
    15.0,
    8.5,
    5.2,
    3.7,
]
BACKFILL_PARALLAX_DEPTH = 3.15


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

    # 2048 worked for compatibility, but oversized layer canvases meant that the
    # visible viewport used substantially fewer than 2048 texels. 3072 restores
    # much of that lost effective resolution while staying reasonably sized.
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

    screen_width, screen_height = 1290, 2796
    aspect = screen_width / screen_height

    # Build painter order from visually deepest stage outward so upper plates
    # cover lower stages during overlap. Keep the normal perspective geometry
    # untouched so circles stay circular and X/Y use the same projection model.
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
        screen_width,
        screen_height,
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
                "Six full-screen texture slices; current-plate soft hole "
                "highlights; inner-to-outer painter order; normal perspective "
                "geometry with globally reversed device-motion response."
            ),
            "layerCount": len(PARALLAX_DEPTHS),
            "parallaxDepthsOuterToInner": PARALLAX_DEPTHS,
            "layerOverscansOuterToInner": OVERSCANS,
            "backgroundOverscan": BACKGROUND_OVERSCAN,
            "compositingOrder": "inner-to-outer",
            "textureSize": args.texture_size,
            "astcQuality": args.astc_quality,
        }
    )

    # Reverse the renderer's device-motion response on both axes without
    # distorting the layer geometry.
    project["camera"]["motionRange"] = -0.025
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
    print(f"parallax depths outer -> inner: {PARALLAX_DEPTHS}")
    print(f"overscans outer -> inner: {OVERSCANS}")
    print("camera motion direction: reversed (motionRange=-0.025)")
    print(
        f"texture: {args.texture_size}x{args.texture_size}, "
        f"ASTC quality={args.astc_quality}"
    )
    print("draw/compositing order: inner -> outer")


if __name__ == "__main__":
    main()
