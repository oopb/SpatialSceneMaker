from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SSM3_MAGIC = b"SSM3"
SST3_MAGIC = b"SST3"
SSM3_VERSION = 1
SST3_VERSION = 1
SSM3_VERTEX_STRIDE = 32
SSM3_INDEX_TYPE_U32 = 1
METAL_ASTC_4X4_SRGB = 186


@dataclass(frozen=True)
class Vertex:
    x: float
    y: float
    z: float
    u: float
    v: float
    texture_slice: int = 0


def write_ssmesh(path: Path, vertices: Iterable[Vertex], indices: Iterable[int]) -> None:
    vertices = list(vertices)
    indices = list(indices)
    if len(indices) % 3:
        raise ValueError("index count must be divisible by 3")
    header = struct.pack(
        "<4s7I", SSM3_MAGIC, SSM3_VERSION, len(vertices), len(indices),
        len(indices) // 3, SSM3_VERTEX_STRIDE, SSM3_INDEX_TYPE_U32, 0,
    )
    with path.open("wb") as f:
        f.write(header)
        for v in vertices:
            f.write(struct.pack("<4f2f2I", v.x, v.y, v.z, 0.0, v.u, v.v, v.texture_slice, 0))
        f.write(struct.pack(f"<{len(indices)}I", *indices))


def write_sstexture(
    path: Path,
    astc_payloads: list[bytes],
    width: int = 2048,
    height: int = 2048,
) -> None:
    if width % 4 or height % 4:
        raise ValueError("ASTC 4x4 dimensions must be divisible by 4")
    bytes_per_image = (width // 4) * (height // 4) * 16
    for payload in astc_payloads:
        if len(payload) != bytes_per_image:
            raise ValueError(f"expected {bytes_per_image} ASTC bytes, got {len(payload)}")
    # Observed files report width*4 here even though ASTC storage itself is block-compressed.
    bytes_per_row = width * 4
    header = struct.pack(
        "<4s9I", SST3_MAGIC, SST3_VERSION, METAL_ASTC_4X4_SRGB,
        width, height, len(astc_payloads), 1, bytes_per_row, bytes_per_image, 40,
    )
    with path.open("wb") as f:
        f.write(header)
        for payload in astc_payloads:
            f.write(payload)
