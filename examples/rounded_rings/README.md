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

The six rings use these outer sizes, top -> bottom:

```text
 420 x  700, radius  95
 560 x  930, radius 125
 710 x 1190, radius 155
 860 x 1480, radius 188
1020 x 1810, radius 225
1180 x 2240, radius 265
```

Except for the first ring's center opening, each ring's inner rounded rectangle
is exactly the previous ring's outer rounded rectangle. This keeps the nested
bands continuous at rest.

The first inner opening is:

```text
260 x 460, radius 62
```

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
