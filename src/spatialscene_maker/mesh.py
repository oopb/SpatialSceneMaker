from __future__ import annotations

import math
import numpy as np
from PIL import Image

from .formats import Vertex


def load_depth(
    path: str,
    out_w: int,
    out_h: int,
    near: float,
    far: float,
    invert: bool = False,
    *,
    discrete: bool = False,
) -> np.ndarray:
    if not (0 < near < far):
        raise ValueError("require 0 < near < far")
    im = Image.open(path)
    arr = np.asarray(im)
    if arr.ndim == 3:
        arr = arr[..., 0]
    maxv = float(np.iinfo(arr.dtype).max) if np.issubdtype(arr.dtype, np.integer) else float(np.nanmax(arr) or 1.0)
    norm = np.clip(arr.astype(np.float32) / maxv, 0.0, 1.0)
    if invert:
        norm = 1.0 - norm
    # Default: white is near. Interpolate inverse depth because disparity is approximately inverse-depth.
    inv = norm / near + (1.0 - norm) / far
    depth = 1.0 / inv
    resample = Image.Resampling.NEAREST if discrete else Image.Resampling.BILINEAR
    dimg = Image.fromarray(depth.astype(np.float32), mode="F").resize((out_w, out_h), resample)
    return np.asarray(dimg, dtype=np.float32)


def build_grid_mesh(depth: np.ndarray, aspect: float, vertical_fov_deg: float, texture_size: int = 2048):
    h, w = depth.shape
    fy = 1.0 / math.tan(math.radians(vertical_fov_deg) * 0.5)
    fx = fy / aspect
    vertices: list[Vertex] = []
    half_texel = 0.5 / texture_size

    for j in range(h):
        ny = 1.0 - 2.0 * (j / max(h - 1, 1))
        v = half_texel + (1.0 - 2.0 * half_texel) * (j / max(h - 1, 1))
        for i in range(w):
            nx = 2.0 * (i / max(w - 1, 1)) - 1.0
            u = half_texel + (1.0 - 2.0 * half_texel) * (i / max(w - 1, 1))
            d = float(depth[j, i])
            x = nx * d / fx
            y = ny * d / fy
            vertices.append(Vertex(x, y, -d, u, v, 0))

    indices: list[int] = []
    for j in range(h - 1):
        for i in range(w - 1):
            a = j * w + i
            b = a + 1
            c = a + w
            d = c + 1
            # Matches the winding observed in SpatialSceneWallpaper samples.
            indices.extend((a, c, b, b, c, d))
    return vertices, indices
