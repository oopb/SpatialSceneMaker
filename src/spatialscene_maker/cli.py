from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

from .formats import write_ssmesh, write_sstexture
from .mesh import build_grid_mesh, load_depth
from .project import build_v3_project, expanded_vertical_fov_rad
from .texture import encode_astc_4x4_srgb


def _backfill_mesh(aspect: float, main_fov_deg: float, far: float, texture_size: int = 2048):
    d0 = far * 1.05
    d1 = d0 + max(1e-3, far * 1e-4)
    depth = np.array([[d0, d0], [d1, d1]], dtype=np.float32)
    expanded_deg = math.degrees(expanded_vertical_fov_rad(main_fov_deg, 1.16))
    vertices, indices = build_grid_mesh(depth, aspect, expanded_deg, texture_size)
    return vertices, indices, (d0, d1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate an experimental SpatialScene V3 bundle.")
    ap.add_argument("image")
    ap.add_argument("depth")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--near", type=float, default=1.0)
    ap.add_argument("--far", type=float, default=10.0)
    ap.add_argument("--fov", type=float, default=45.0, help="vertical FOV in degrees")
    ap.add_argument("--grid-width", type=int, default=65)
    ap.add_argument("--texture-size", type=int, default=2048)
    ap.add_argument("--depth-mode", choices=("continuous", "discrete"), default="continuous")
    ap.add_argument("--invert-depth", action="store_true")
    ap.add_argument("--astcenc")
    ap.add_argument("--scene-id", help="optional stable UUID for project.json")
    args = ap.parse_args()

    image = Image.open(args.image)
    width, height = image.size
    aspect = width / height
    grid_w = max(2, args.grid_width)
    grid_h = max(2, round(grid_w / aspect))

    out = Path(args.output)
    if out.suffix != ".spatialscene":
        out = out.with_suffix(".spatialscene")
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    depth = load_depth(
        args.depth,
        grid_w,
        grid_h,
        args.near,
        args.far,
        args.invert_depth,
        discrete=args.depth_mode == "discrete",
    )
    main_vertices, main_indices = build_grid_mesh(depth, aspect, args.fov, args.texture_size)
    write_ssmesh(assets / "main.ssmesh", main_vertices, main_indices)

    back_vertices, back_indices, back_depth_range = _backfill_mesh(
        aspect, args.fov, args.far, args.texture_size
    )
    write_ssmesh(assets / "backfill.ssmesh", back_vertices, back_indices)

    payload = encode_astc_4x4_srgb(args.image, args.texture_size, args.astcenc)
    write_sstexture(assets / "main.sstexture", [payload], args.texture_size, args.texture_size)
    write_sstexture(assets / "backfill.sstexture", [payload], args.texture_size, args.texture_size)

    main_depth_range = (float(depth.min()), float(depth.max()))
    project = build_v3_project(
        width,
        height,
        args.fov,
        main_depth_range,
        back_depth_range,
        scene_id=args.scene_id,
    )
    (out / "project.json").write_text(
        json.dumps(project, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Generated: {out}")
    print(
        f"main: {len(main_vertices)} vertices, {len(main_indices)//3} triangles, "
        f"depth {main_depth_range[0]:.6g}..{main_depth_range[1]:.6g}"
    )
    print(
        f"backfill: {len(back_vertices)} vertices, {len(back_indices)//3} triangles, "
        f"depth {back_depth_range[0]:.6g}..{back_depth_range[1]:.6g}"
    )


if __name__ == "__main__":
    main()
