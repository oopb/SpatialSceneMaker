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

# Illusion-oriented parallax profile:
# large camera-space depth = smaller apparent motion;
# small camera-space depth = larger apparent motion.
# Therefore the outer rim is nearly stationary and the visually deeper center
# moves progressively more.
PARALLAX_DEPTHS = [
    40.0,
    25.0,
    17.0,
    12.0,
    8.8,
    6.7,
    5.3,
    4.35,
    3.65,
]
BACKFILL_PARALLAX_DEPTH = 3.1


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
            f"Expected {len(PARALLAX_DEPTHS)} slices, found {len(slices)} in {asset_dir}"
        )

    bg_path = asset_dir / "background.png"
    if not bg_path.exists():
        raise SystemExit(f"Missing {bg_path}")

    screen_width, screen_height = 1290, 2796
    aspect = screen_width / screen_height

    meshes = []
    for idx, (depth, overscan) in enumerate(zip(PARALLAX_DEPTHS, OVERSCANS)):
        meshes.append(
            build_full_frame_quad(
                depth,
                aspect,
                args.fov,
                texture_size=args.texture_size,
                texture_slice=idx,
                overscan=overscan,
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
            "name": "SpatialSceneMaker layered gravity",
            "strategy": (
                "Nine transparent texture slices with progressively larger "
                "overscan and recessed-motion parallax profile."
            ),
            "layerCount": len(PARALLAX_DEPTHS),
            "parallaxDepths": PARALLAX_DEPTHS,
            "layerOverscans": OVERSCANS,
            "backgroundOverscan": BACKGROUND_OVERSCAN,
        }
    )
    project["camera"]["motionRange"] = 0.030
    project["camera"]["overscan"] = 0.020

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
    print(f"parallax depths (outer -> inner): {PARALLAX_DEPTHS}")
    print(f"overscans (outer -> inner): {OVERSCANS}")
    print(f"backfill overscan: {BACKGROUND_OVERSCAN}")


if __name__ == "__main__":
    main()
