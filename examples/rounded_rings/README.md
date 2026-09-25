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

All six rings are concentric and use true **ring-within-ring** nesting.

From top to bottom:

- the outer rounded rectangle continuously becomes larger;
- the inner rounded rectangle continuously becomes smaller.

So each complete upper ring lies inside the visible band of the next lower
ring: the lower layer reaches farther outward and its hole reaches farther
inward.

Outer sizes, top -> bottom:

```text
390 x  607, radius  98
460 x  716, radius 115
543 x  845, radius 136
641 x  997, radius 160
756 x 1176, radius 189
892 x 1388, radius 223
```

The outer geometry uses a compact, approximately constant `1.18x` scale from
one layer to the next. Width, height, and corner radius are scaled together, so
the outer rounded rectangles keep the same proportions. Compared with the
previous version, the top outer ring is slightly larger for more thickness,
while progressively deeper outer rings are compressed much more.

Inner openings, top -> bottom:

```text
240 x 380, radius 58
200 x 315, radius 48
165 x 255, radius 39
130 x 200, radius 31
100 x 150, radius 24
 70 x 105, radius 17
```

The inner openings are unchanged from the previous version. The generator still
validates both monotonic directions: outer bounds/radii must grow and inner
openings/radii must shrink.

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
