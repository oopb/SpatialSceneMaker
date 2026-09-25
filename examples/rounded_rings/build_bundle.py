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

from make_assets import (
    BACKGROUND_OVERSCAN,
    BOTTOM_COLOR,
    H,
    OVERSCANS,
    RINGS,
    W,
)

# Top -> bottom motion amplitudes.
# The top rounded ring moves the most; every deeper layer moves less.
MOTION_AMPLITUDES = [1.00, 0.85, 0.70, 0.55, 0.40, 0.25, 0.10]
PARALLAX_DEPTHS = [
    1.0 / amplitude
    for amplitude in MOTION_AMPLITUDES
]

# Put the safety backfill slightly behind the bottom layer.
BACKFILL_PARALLAX_DEPTH = 12.0


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build the rounded-ring layered SpatialScene bundle"
    )
    ap.add_argument(
        "asset_dir",
        nargs="?",
        default="examples/rounded_rings/assets",
    )
    ap.add_argument(
        "-o",
        "--output",
        default="RoundedRings.spatialscene",
    )
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
            f"{asset_dir}. Run make_assets.py again so stale slices are removed."
        )

    bg_path = asset_dir / "background.png"
    if not bg_path.exists():
        raise SystemExit(f"Missing {bg_path}")

    aspect = W / H

    # Draw deepest -> topmost. The bottom full-screen plate is written first,
    # then progressively smaller/brighter rounded rings are layered above it.
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
            "name": "SpatialSceneMaker rounded rings",
            "strategy": (
                "Six centered rounded-rectangle rings plus one full-screen "
                "bottom layer; ring size increases, color darkens, and motion "
                "amplitude decreases with depth."
            ),
            "layerCount": len(PARALLAX_DEPTHS),
            "ringCount": len(RINGS),
            "motionAmplitudesTopToBottom": MOTION_AMPLITUDES,
            "parallaxDepthsTopToBottom": PARALLAX_DEPTHS,
            "layerOverscansTopToBottom": OVERSCANS,
            "bottomColor": list(BOTTOM_COLOR),
            "compositingOrder": "bottom-to-top",
            "textureSize": args.texture_size,
            "astcQuality": args.astc_quality,
        }
    )

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
    print(f"motion amplitudes top -> bottom: {MOTION_AMPLITUDES}")
    print(f"parallax depths top -> bottom: {PARALLAX_DEPTHS}")
    print(f"overscans top -> bottom: {OVERSCANS}")
    print("camera: motionRange=+0.035, overscan=0.015")
    print("draw/compositing order: bottom -> top")


if __name__ == "__main__":
    main()
