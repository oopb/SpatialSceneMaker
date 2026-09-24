from __future__ import annotations

import shutil
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


def encode_astc_4x4_srgb_pil(image: Image.Image, size: int = 2048, executable: str | None = None) -> bytes:
    exe = _find_astcenc(executable)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        png = td / "texture.png"
        astc = td / "texture.astc"
        image.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS).save(png)
        subprocess.run([exe, "-cs", str(png), str(astc), "4x4", "-medium"], check=True)
        data = astc.read_bytes()
    if len(data) < 16 or data[:4] != ASTC_MAGIC:
        raise RuntimeError("astcenc output is not an ASTC file")
    return data[16:]


def encode_astc_4x4_srgb(image_path: str, size: int = 2048, executable: str | None = None) -> bytes:
    im = Image.open(image_path)
    return encode_astc_4x4_srgb_pil(im, size=size, executable=executable)
