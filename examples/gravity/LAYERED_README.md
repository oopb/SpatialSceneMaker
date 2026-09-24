# Layered gravity demo

This demo uses **eight full-screen texture slices**:

- six full-screen plates with geometrically similar rounded-rectangle cut-outs;
- one full-screen plate with the preserved circular cut-out;
- one full-screen bottom image.

There is no highlight / glow overlay.

## Stronger color contrast

Adjacent layers use separated green/teal values so the eight-stage stack remains
readable without synthetic edge lighting.

## Smaller inner openings

The central circle is reduced to approximately half of the previous radius:

```text
center = (645, 1465)
radius = 82
diameter = 164
```

The smallest rounded opening is also reduced:

```text
300 x 356
corner radius = 51
```

All six rounded openings remain uniform scales of the same base shape. Their
current outer -> inner geometry is approximately:

```text
1020 x 1210, r=173
 799 x  948, r=136
 625 x  742, r=106
 489 x  581, r=83
 383 x  455, r=65
 300 x  356, r=51
circle diameter 164
```

## Layer height

Height above the bottom remains proportional to the opening perimeter.

The current depth range remains:

```text
outer depth = 75.0
inner depth = 3.7
```

With the smaller inner windows, the generated depths are approximately:

```text
75.000
59.543
47.409
37.911
30.494
24.671
12.524
 3.700
```

## Motion direction and amplitude

The previous negative sign is removed and the motion amplitude is increased
substantially:

```text
camera.motionRange = 0.05
```

This restores the positive offset direction and doubles the earlier 0.025 motion
amplitude.

## Overscan

```text
1.035, 1.048, 1.062, 1.082, 1.105, 1.135, 1.18, 1.24
```

## Texture quality

The layered builder defaults to:

```text
texture size = 3072x3072
ASTC quality = thorough
```

## Build

```powershell
git pull
python -m pip install -e .

python examples/gravity/make_layered_assets.py

python examples/gravity/build_layered_bundle.py `
  examples/gravity/layered_assets `
  -o GravityLayered.spatialscene `
  --fov 45 `
  --astcenc "astcenc-5.7.0-windows-x64/bin/astcenc-avx2.exe" `
  --texture-size 3072 `
  --astc-quality thorough
```
