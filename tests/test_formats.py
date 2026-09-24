import struct
from pathlib import Path

from spatialscene_maker.formats import Vertex, write_ssmesh, write_sstexture


def test_ssmesh_layout(tmp_path: Path):
    p = tmp_path / "x.ssmesh"
    vertices = [
        Vertex(0, 0, -1, 0.25, 0.25),
        Vertex(1, 0, -1, 0.75, 0.25),
        Vertex(0, 1, -1, 0.25, 0.75),
    ]
    write_ssmesh(p, vertices, [0, 1, 2])
    data = p.read_bytes()
    h = struct.unpack("<4s7I", data[:32])
    assert h == (b"SSM3", 1, 3, 3, 1, 32, 1, 0)
    assert len(data) == 32 + 3 * 32 + 3 * 4


def test_sstexture_layout(tmp_path: Path):
    p = tmp_path / "x.sstexture"
    size = 8
    payload_size = (size // 4) * (size // 4) * 16
    write_sstexture(p, [bytes(payload_size)], size, size)
    data = p.read_bytes()
    h = struct.unpack("<4s9I", data[:40])
    assert h == (b"SST3", 1, 186, 8, 8, 1, 1, 32, payload_size, 40)
    assert len(data) == 40 + payload_size
