# Rounded rings wallpaper

This demo is independent from the existing gravity wallpaper.

It uses seven main depth layers:

- six centered rounded-rectangle **rings**;
- one full-screen bottom layer.

Each ring is a rounded rectangle with a smaller rounded rectangle cut out of its
center. Moving from top to bottom:

- the ring becomes larger;
- the color becomes darker;
- the motion amplitude becomes smaller.

The deepest layer is a full-screen dark fill.

## Geometry

All six rings are concentric. From top to bottom, every ring is strictly larger
than the one above it in both width and height, so the complete upper rounded
rectangle sits inside the next lower rounded rectangle instead of merely
touching its opening.

Outer sizes, top -> bottom:

```text
 360 x  560, radius  90
 520 x  820, radius 125
 700 x 1120, radius 165
 880 x 1460, radius 205
1040 x 1830, radius 245
1190 x 2280, radius 285
```

The center openings are intentionally much smaller, making every ring
substantially thicker:

```text
120 x 190, radius  38
180 x 290, radius  52
250 x 400, radius  70
320 x 530, radius  88
390 x 680, radius 106
470 x 860, radius 130
```

The asset generator validates both constraints: upper-to-lower containment and
an opening smaller than half of the corresponding outer width/height.

## Color

The palette transitions from bright teal-green on the top ring to a very dark
teal bottom surface.

## Motion profile

Motion amplitude decreases linearly-ish from top to bottom:

```text
1.00
0.85
0.70
0.55
0.40
0.25
0.10
```

Because apparent parallax is approximately proportional to `1/depth`, the
corresponding camera-space depths are:

```text
1.000000
1.176471
1.428571
1.818182
2.500000
4.000000
10.000000
```

The top ring therefore moves the most and the full-screen bottom layer moves the
least.

## Build

```powershell
git pull
python -m pip install -e .

python examples/rounded_rings/make_assets.py

python examples/rounded_rings/build_bundle.py `
  examples/rounded_rings/assets `
  -o RoundedRings.spatialscene `
  --fov 45 `
  --astcenc "astcenc-5.7.0-windows-x64/bin/astcenc-avx2.exe" `
  --texture-size 3072 `
  --astc-quality thorough
```
