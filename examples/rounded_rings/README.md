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
 360 x  560, radius  90
 520 x  820, radius 125
 700 x 1120, radius 165
 880 x 1460, radius 205
1040 x 1830, radius 245
1190 x 2280, radius 285
```

Inner openings, top -> bottom:

```text
240 x 380, radius 58
200 x 315, radius 48
165 x 255, radius 39
130 x 200, radius 31
100 x 150, radius 24
 70 x 105, radius 17
```

The generator validates both monotonic directions: outer bounds/radii must grow
and inner openings/radii must shrink.

## Color

The palette transitions from bright teal-green on the top ring to a very dark
teal bottom surface.

Each ring also has a soft inner-rim highlight. The highlight is generated from
the existing inner rounded-rectangle mask, blurred outward into the visible ring
and blended with a brighter tint. All six rings use the same highlight strength;
there is no depth-dependent brightening. This does not change any inner or outer
geometry.

The full-screen bottom layer has a centered light-aperture effect. The aperture
is now a slightly larger `40x64` rounded rectangle with radius `12`, still
smaller than the smallest `70x105` ring opening. Its center remains almost
white (`252,255,254`). The rounded-rectangle transition now spreads much
farther outward: the tight, medium, and wide Gaussian halo radii are
`12 / 36 / 72`, giving the light a broader and more gradual falloff into the
dark surface while still preserving the rectangular character close to the
opening. The safety backfill remains flat and does not receive this center
highlight.

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
