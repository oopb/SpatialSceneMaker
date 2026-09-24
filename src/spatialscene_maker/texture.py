from __future__ import annotations

import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ASTC_MAGIC = b"\x13\xab\xa1\x5c"


def _find_astcenc(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    for name in ("astcenc", "astcenc-avx2", "astcenc-sse4.1", "astcenc-neon"):
        p = shutil.which(name)
        if p:
            return p
    raise RuntimeError("astcenc not found; install ARM astcenc or pass --astcenc")


def encode_astc_4x4_srgb(image_path: str, size: int = 2048, executable: str | None = None) -> bytes:
    exe = _find_astcenc(executable)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        png = td / "texture.png"
        astc = td / "texture.astc"
        im = Image.open(image_path).convert("RGBA")
        im.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        x = (size - im.width) // 2
        y = (size - im.height) // 2
        canvas.alpha_composite(im, (x, y))
        canvas.save(png)
        subprocess.run([exe, "-cs", str(png), str(astc), "4x4", "-medium"], check=True)
        data = astc.read_bytes()
    if len(data) < 16 or data[:4] != ASTC_MAGIC:
        raise RuntimeError("astcenc output is not an ASTC file")
    # Standard .astc has a 16-byte header. SST3 stores only compressed blocks.
    return data[16:]
