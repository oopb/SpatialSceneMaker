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
    ap = argparse.ArgumentParser(description="Build the layered gravity SpatialScene bundle")
    ap.add_argument("asset_dir", nargs="?", default="examples/gravity/layered_assets")
    ap.add_argument("-o", "--output", default="GravityLayered.spatialscene")
    ap.add_argument("--fov", type=float, default=45.0)
    ap.add_argument("--texture-size", type=int, default=2048)
    ap.add_argument("--astcenc")
    ap.add_argument("--scene-id")
    args = ap.parse_args()

    asset_dir = Path(args.asset_dir)
    slices = sorted(asset_dir.glob("slice_*.png"))
    if len(slices) != len(PARALLAX_DEPTHS):
        raise SystemExit(
            f"Expected {len(PARALLAX_DEPTHS)} slices, found {len(slices)} in {asset_dir}. "
            "Run make_layered_assets.py again so stale slices are removed."
        )

    bg_path = asset_dir / "background.png"
    if not bg_path.exists():
        raise SystemExit(f"Missing {bg_path}")

    screen_width, screen_height = 1290, 2796
    aspect = screen_width / screen_height

    # IMPORTANT: build painter order from the visually deepest stage outward.
    # The outer/top rings are appended last. If the renderer's transparent pass
    # honors index order (as observed in the current app), this makes inner
    # stages disappear behind the rim when they overlap during tilt, reading as
    # a cavity rather than as a stack protruding toward the viewer.
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

    backfill_fov_deg = math.degrees(expanded_vertical_fov_rad(args.fov, 1.16))
    backfill_vertices, backfill_indices = build_full_frame_quad(
        BACKFILL_PARALLAX_DEPTH,
        aspect,
        backfill_fov_deg,
        texture_size=args.texture_size,
        texture_slice=0,
        overscan=BACKGROUND_OVERSCAN,
    )

    print("Encoding ASTC slices...")
    payloads = [
        encode_astc_4x4_srgb_pil(
            Image.open(path).convert("RGBA"),
            size=args.texture_size,
            executable=args.astcenc,
        )
        for path in slices
    ]
    bg_payload = encode_astc_4x4_srgb_pil(
        Image.open(bg_path).convert("RGBA"),
        size=args.texture_size,
        executable=args.astcenc,
    )

    out = Path(args.output)
    if out.suffix != ".spatialscene":
        out = out.with_suffix(".spatialscene")
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    write_ssmesh(assets / "main.ssmesh", main_vertices, main_indices)
    write_ssmesh(assets / "backfill.ssmesh", backfill_vertices, backfill_indices)
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
        (BACKFILL_PARALLAX_DEPTH, BACKFILL_PARALLAX_DEPTH + 0.001),
        scene_id=args.scene_id,
    )
    project["generator"].update(
        {
            "name": "SpatialSceneMaker recessed gravity",
            "strategy": (
                "Six transparent texture slices; inner-to-outer painter order; "
                "upper stages move less and lower stages move more."
            ),
            "layerCount": len(PARALLAX_DEPTHS),
            "parallaxDepthsOuterToInner": PARALLAX_DEPTHS,
            "layerOverscansOuterToInner": OVERSCANS,
            "backgroundOverscan": BACKGROUND_OVERSCAN,
            "compositingOrder": "inner-to-outer",
        }
    )

    # Keep global motion conservative: the per-stage depth ratio already creates
    # a large differential between the outer rim and the center.
    project["camera"]["motionRange"] = 0.025
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
    print("draw/compositing order: inner -> outer")


if __name__ == "__main__":
    main()
