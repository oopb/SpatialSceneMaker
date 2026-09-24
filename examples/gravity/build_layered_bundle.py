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
    DEPTH_GRAYS,
    H,
    OVERSCANS,
    W,
)

# Match the reference make_assets.py / GravityWallpaper.spatialscene depth model:
# --near 1 --far 8 with the exact discrete grayscale levels.
NEAR_DEPTH = 1.0
FAR_DEPTH = 8.0


def _depth_from_gray(gray: int) -> float:
    norm = gray / 255.0
    inv_depth = norm / NEAR_DEPTH + (1.0 - norm) / FAR_DEPTH
    return 1.0 / inv_depth


SOURCE_PARALLAX_DEPTHS = [
    _depth_from_gray(gray)
    for gray in DEPTH_GRAYS
]

# Keep exactly the same seven depth magnitudes as the previous reference-like
# version, but assign them in the opposite layer order. This fully reverses the
# per-layer motion amplitudes while preserving all inter-layer proportions.
PARALLAX_DEPTHS = list(reversed(SOURCE_PARALLAX_DEPTHS))

# The supplied reference bundle uses 8.4 for its V3 backfill plane.
BACKFILL_PARALLAX_DEPTH = 8.4


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

    # Every slice is a full-screen plate, so build deepest -> outermost.
    # This lets the outer plates cover deeper plates everywhere except through
    # their cut-outs.
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
            "name": "SpatialSceneMaker make_assets layered reference",
            "strategy": (
                "Seven full-screen cutout plates reconstructed from "
                "make_assets.py: five nested rounded cut-outs, one circular "
                "cut-out, and one full-screen bottom plate; exact make_assets "
                "source depth-map levels and reference camera direction; "
                "the previous per-layer motion amplitudes are assigned in "
                "the exact opposite order while preserving their proportions."
            ),
            "layerCount": len(PARALLAX_DEPTHS),
            "sourceDepthGraysOuterToInner": DEPTH_GRAYS,
            "sourceParallaxDepthsOuterToInner": SOURCE_PARALLAX_DEPTHS,
            "parallaxDepthsOuterToInner": PARALLAX_DEPTHS,
            "layerOverscansOuterToInner": OVERSCANS,
            "backgroundOverscan": BACKGROUND_OVERSCAN,
            "compositingOrder": "inner-to-outer",
            "textureSize": args.texture_size,
            "astcQuality": args.astc_quality,
        }
    )

    # Commit-history check:
    # - ef4ee9a: +0.030 (first layered implementation)
    # - e021f35..58da483: +0.025 (stable six-layer period)
    # - 8883b84: first negative motionRange experiment
    #
    # The supplied reference GravityWallpaper.spatialscene itself uses +0.035,
    # so restore that exact positive camera direction and amplitude.
    project["camera"]["motionRange"] = 0.035
    project["camera"]["overscan"] = 0.015

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
    print(f"depth grays outer -> inner: {DEPTH_GRAYS}")
    print(f"source depths outer -> inner: {SOURCE_PARALLAX_DEPTHS}")
    print(f"reversed parallax depths outer -> inner: {PARALLAX_DEPTHS}")
    print(f"overscans outer -> inner: {OVERSCANS}")
    print("camera: motionRange=+0.035, overscan=0.015")
    print("draw/compositing order: inner -> outer")


if __name__ == "__main__":
    main()
