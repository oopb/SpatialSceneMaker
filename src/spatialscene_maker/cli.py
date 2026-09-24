from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

from PIL import Image

from .formats import Vertex, write_ssmesh, write_sstexture
from .mesh import build_grid_mesh, load_depth
from .texture import encode_astc_4x4_srgb


def _project(width: int, height: int, fov_deg: float, near: float, far: float) -> dict:
    return {
        "schemaVersion": 3,
        "renderer": "depth-field-v3",
        "generator": {
            "name": "SpatialSceneMaker",
            "experimental": True,
            "inputMode": "custom-depth-map",
        },
        "metadata": {
            "aspectRatio": width / height,
            "verticalFOV": math.radians(fov_deg),
        },
        "layers": [
            {
                "role": "backfill",
                "mesh": "assets/backfill.ssmesh",
                "texture": "assets/backfill.sstexture",
                "depthRange": [far * 1.05, far * 1.05],
            },
            {
                "role": "main",
                "mesh": "assets/main.ssmesh",
                "texture": "assets/main.sstexture",
                "depthRange": [near, far],
            },
        ],
    }


def _flat_backfill(aspect: float, fov_deg: float, depth: float, texture_size: int = 2048):
    import numpy as np
    d = np.full((2, 2), depth, dtype=np.float32)
    return build_grid_mesh(d, aspect, fov_deg, texture_size)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate an experimental SpatialScene V3 bundle.")
    ap.add_argument("image")
    ap.add_argument("depth")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--near", type=float, default=1.0)
    ap.add_argument("--far", type=float, default=10.0)
    ap.add_argument("--fov", type=float, default=45.0, help="vertical FOV in degrees")
    ap.add_argument("--grid-width", type=int, default=129)
    ap.add_argument("--texture-size", type=int, default=2048)
    ap.add_argument("--invert-depth", action="store_true")
    ap.add_argument("--astcenc")
    args = ap.parse_args()

    image = Image.open(args.image)
    aspect = image.width / image.height
    grid_w = max(2, args.grid_width)
    grid_h = max(2, round(grid_w / aspect))

    out = Path(args.output)
    if out.suffix != ".spatialscene":
        out = out.with_suffix(".spatialscene")
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    depth = load_depth(args.depth, grid_w, grid_h, args.near, args.far, args.invert_depth)
    vertices, indices = build_grid_mesh(depth, aspect, args.fov, args.texture_size)
    write_ssmesh(assets / "main.ssmesh", vertices, indices)

    back_depth = args.far * 1.05
    back_vertices, back_indices = _flat_backfill(aspect, args.fov, back_depth, args.texture_size)
    write_ssmesh(assets / "backfill.ssmesh", back_vertices, back_indices)

    payload = encode_astc_4x4_srgb(args.image, args.texture_size, args.astcenc)
    write_sstexture(assets / "main.sstexture", [payload], args.texture_size, args.texture_size)
    write_sstexture(assets / "backfill.sstexture", [payload], args.texture_size, args.texture_size)

    (out / "project.json").write_text(
        json.dumps(_project(image.width, image.height, args.fov, args.near, args.far), indent=2),
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
