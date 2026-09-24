from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

W, H = 1290, 2796
LEVELS = [
    # (margin_x, top, bottom, radius, rgb, depth-gray)
    (95, 720, 2190, 150, (16, 77, 67), 220),
    (155, 805, 2105, 135, (24, 111, 93), 185),
    (220, 900, 2010, 120, (36, 146, 119), 150),
    (290, 1000, 1910, 105, (54, 181, 146), 115),
    (365, 1110, 1800, 90, (81, 207, 170), 80),
]


def rounded(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def build(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (W, H), (7, 48, 43))
    depth = Image.new("L", (W, H), 255)
    di = ImageDraw.Draw(img)
    dd = ImageDraw.Draw(depth)

    # Very subtle vignette/vertical shading, kept inside each flat-depth region.
    for y in range(H):
        t = y / (H - 1)
        c = (7 + int(3*t), 48 + int(7*t), 43 + int(5*t))
        di.line((0, y, W, y), fill=c)

    for mx, top, bottom, r, color, gray in LEVELS:
        box = (mx, top, W-mx, bottom)
        rounded(di, box, r, color)
        rounded(dd, box, r, gray)

    # Deep center: a circle, matching the nested geometry but using an original palette.
    cx, cy, radius = W//2, 1455, 205
    di.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(137, 231, 207))
    dd.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=45)

    # Gentle highlight in the center without changing its discrete depth.
    glow = Image.new("RGBA", (W, H), (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((cx-155, cy-155, cx+155, cy+155), fill=(225,255,247,40))
    glow = glow.filter(ImageFilter.GaussianBlur(55))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    img.save(out_dir / "gravity-wallpaper.png", quality=95)
    depth.save(out_dir / "gravity-depth.png")
    print(out_dir / "gravity-wallpaper.png")
    print(out_dir / "gravity-depth.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples/gravity/assets")
    args = ap.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
